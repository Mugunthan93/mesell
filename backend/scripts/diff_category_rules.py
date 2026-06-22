"""diff_category_rules.py — category snapshot diff engine for the change monitor.

Generalises diff_pricing_lookup.py from pricing rows keyed by sscat_id to the
FOUR category rule dimensions produced by scrape_category.py:

    compliance_fields  — required/optional field flips, new mandatory fields
    shipping_slab      — shipping_charges / gst_percentage changes
    banned_words       — newly added / removed banned word entries
    cost_fields        — transfer_price / platform_fee changes

Design decisions
----------------
1.  content_hash short-circuit (checked BEFORE the dimension diff):
    If new_hash == prev_hash the dimensions are byte-identical — return PASS
    with empty sets immediately.  This mirrors diff_pricing_lookup.py's
    generated_at exclusion discipline: stable metadata fields are never part
    of the hash, so a byte-identical hash means ZERO rule surface change.
    W4 (the fan-out worker) must check for the BLOCK verdict before acting —
    it MUST NOT fan out on a BLOCK.

2.  BLOCK on scrape anomaly — a truncated or partial projection (missing any
    of the four mandatory dimensions) is a hard BLOCK.  W4 must not fan out
    on a BLOCK.

3.  BLOCK / REVIEW_REQUIRED / PASS precedence (identical to diff_pricing_lookup.py):
    BLOCK > REVIEW_REQUIRED > PASS.

4.  Founder-overridable per-dimension thresholds (clearly marked at module level).
    Setting a threshold to 0 turns any non-zero drift for that dimension into BLOCK.

5.  Stdlib-only.  No DB, no network.

6.  W2 emits the STRUCTURED diff only.  Seller-facing copy (human-readable
    notification text) is W4's responsibility — not generated here.

Public API
----------
    diff_category_snapshot(new_dims, prev_dims, *, prev_hash=None, new_hash=None)
        -> dict  (the structured diff result)

    render_diff_report(result, run_date=None)
        -> str   (markdown report, suitable for a PR body or log file)

Exit codes (CLI):
    0 = PASS, 1 = REVIEW_REQUIRED, 2 = BLOCK

Stdlib-only.  No new dependencies.

CLI usage (operator / debugging):
    python backend/scripts/diff_category_rules.py NEW_SNAPSHOT.json PREV_SNAPSHOT.json
           [--new-hash HEX] [--prev-hash HEX]
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Verdict strings — reused verbatim from diff_pricing_lookup.py
# (stable interface for callers including W4 fan-out worker)
# ---------------------------------------------------------------------------
VERDICT_PASS = "PASS"
VERDICT_REVIEW = "REVIEW_REQUIRED"
VERDICT_BLOCK = "BLOCK"

# ---------------------------------------------------------------------------
# FOUNDER-OVERRIDABLE DEFAULTS
# These constants set the boundaries between PASS / REVIEW_REQUIRED / BLOCK
# for each dimension.  Setting a constant to 0 turns any non-zero drift for
# that dimension into a BLOCK.
# ---------------------------------------------------------------------------

# compliance_fields — any change to required/optional sets
BLOCK_THRESHOLD_COMPLIANCE_ADDED: int = 9999   # FOUNDER-OVERRIDABLE DEFAULT
BLOCK_THRESHOLD_COMPLIANCE_REMOVED: int = 9999  # FOUNDER-OVERRIDABLE DEFAULT

# shipping_slab — absolute delta in shipping_charges (₹)
BLOCK_THRESHOLD_SHIPPING_DELTA_INR: int = 9999  # FOUNDER-OVERRIDABLE DEFAULT

# banned_words — count of newly added banned words
BLOCK_THRESHOLD_BANNED_ADDED: int = 9999  # FOUNDER-OVERRIDABLE DEFAULT

# cost_fields — absolute delta in transfer_price (₹)
BLOCK_THRESHOLD_COST_DELTA_INR: float = 9999.0  # FOUNDER-OVERRIDABLE DEFAULT

# ---------------------------------------------------------------------------
# Required top-level dimension keys
# A projection missing any of these is a scrape anomaly → BLOCK
# ---------------------------------------------------------------------------
_REQUIRED_DIMENSION_KEYS = frozenset(
    {"compliance_fields", "shipping_slab", "banned_words", "cost_fields"}
)


def _is_partial_projection(dims: dict[str, Any]) -> bool:
    """Return True if the projection is truncated / missing required dimensions."""
    if not isinstance(dims, dict):
        return True
    return not _REQUIRED_DIMENSION_KEYS.issubset(dims.keys())


# ---------------------------------------------------------------------------
# Per-dimension diff helpers
# ---------------------------------------------------------------------------


def _diff_compliance(
    new: dict[str, Any],
    prev: dict[str, Any],
) -> dict[str, Any]:
    """Diff the compliance_fields dimension.

    Compares the ``required`` and ``optional`` field lists.
    Returns a dict with per-list added/removed/changed sets plus a verdict.
    """
    new_req = set(new.get("required", []))
    prev_req = set(prev.get("required", []))
    new_opt = set(new.get("optional", []))
    prev_opt = set(prev.get("optional", []))

    req_added = sorted(new_req - prev_req)
    req_removed = sorted(prev_req - new_req)
    opt_added = sorted(new_opt - prev_opt)
    opt_removed = sorted(prev_opt - new_opt)

    return {
        "required_added": req_added,
        "required_removed": req_removed,
        "optional_added": opt_added,
        "optional_removed": opt_removed,
        "changed": bool(req_added or req_removed or opt_added or opt_removed),
    }


def _diff_shipping(
    new: dict[str, Any],
    prev: dict[str, Any],
) -> dict[str, Any]:
    """Diff the shipping_slab dimension.

    Compares shipping_charges (₹) and gst_percentage (%).
    Returns a dict with old/new values, delta, and a changed flag.
    """
    new_ship = int(new.get("shipping_charges", 0))
    prev_ship = int(prev.get("shipping_charges", 0))
    new_gst = int(new.get("gst_percentage", 0))
    prev_gst = int(prev.get("gst_percentage", 0))

    ship_delta = new_ship - prev_ship
    gst_delta = new_gst - prev_gst

    return {
        "shipping_charges_old": prev_ship,
        "shipping_charges_new": new_ship,
        "shipping_delta": ship_delta,
        "gst_percentage_old": prev_gst,
        "gst_percentage_new": new_gst,
        "gst_delta": gst_delta,
        "changed": bool(ship_delta or gst_delta),
    }


def _diff_banned_words(
    new: dict[str, Any],
    prev: dict[str, Any],
) -> dict[str, Any]:
    """Diff the banned_words dimension.

    Each sub-key (e.g. 'branded', 'trademark') is diffed independently.
    Returns per-key added/removed sets and an overall changed flag.
    """
    all_keys = set(new.keys()) | set(prev.keys())
    per_key: dict[str, dict[str, Any]] = {}
    any_changed = False

    for key in sorted(all_keys):
        new_list = set(new.get(key, []))
        prev_list = set(prev.get(key, []))
        added = sorted(new_list - prev_list)
        removed = sorted(prev_list - new_list)
        changed = bool(added or removed)
        if changed:
            any_changed = True
        per_key[key] = {"added": added, "removed": removed, "changed": changed}

    return {"per_key": per_key, "changed": any_changed}


def _diff_cost_fields(
    new: dict[str, Any],
    prev: dict[str, Any],
) -> dict[str, Any]:
    """Diff the cost_fields dimension.

    Compares transfer_price and platform_fee.
    Returns old/new values, deltas, and a changed flag.
    """
    new_tp = float(new.get("transfer_price", 0))
    prev_tp = float(prev.get("transfer_price", 0))
    new_pf = float(new.get("platform_fee", 0))
    prev_pf = float(prev.get("platform_fee", 0))

    tp_delta = round(new_tp - prev_tp, 4)
    pf_delta = round(new_pf - prev_pf, 4)

    return {
        "transfer_price_old": prev_tp,
        "transfer_price_new": new_tp,
        "transfer_price_delta": tp_delta,
        "platform_fee_old": prev_pf,
        "platform_fee_new": new_pf,
        "platform_fee_delta": pf_delta,
        "changed": bool(tp_delta or pf_delta),
    }


# ---------------------------------------------------------------------------
# Core public API
# ---------------------------------------------------------------------------


def diff_category_snapshot(
    new_dims: dict[str, Any],
    prev_dims: dict[str, Any],
    *,
    prev_hash: str | None = None,
    new_hash: str | None = None,
) -> dict[str, Any]:
    """Compare two category rule dimension projections.

    This is the main entry point consumed by the W3 Celery task (BACKEND-owned)
    and by the CLI.  It ONLY classifies — it does NOT write any file, does NOT
    touch the DB, and does NOT send any notification (that is W4's responsibility).

    Args:
        new_dims:   The newly-captured dimensions_jsonb projection.
        prev_dims:  The previously-stored dimensions_jsonb projection.
        prev_hash:  SHA-256 hex of prev_dims (from category_snapshots.content_hash).
                    If provided and equal to new_hash, returns PASS immediately.
        new_hash:   SHA-256 hex of new_dims (computed by scrape_category.py).
                    If provided and equal to prev_hash, returns PASS immediately.

    Returns:
        A summary dict with the following shape::

            {
                "verdict":          "PASS" | "REVIEW_REQUIRED" | "BLOCK",
                "block_reasons":    [...],   # empty list when not BLOCK
                "review_reasons":   [...],   # empty list when PASS
                "hash_equal":       bool,    # True if hash short-circuit fired
                "compliance_diff":  {...},   # _diff_compliance result
                "shipping_diff":    {...},   # _diff_shipping result
                "banned_words_diff":{...},   # _diff_banned_words result
                "cost_fields_diff": {...},   # _diff_cost_fields result
            }

        The caller (W4 Celery fan-out task) enforces the promotion policy based
        on ``verdict``.  W4 MUST NOT fan out on BLOCK.
    """
    block_reasons: list[str] = []
    review_reasons: list[str] = []

    # --- hash short-circuit (cheapest possible check) ---
    if prev_hash is not None and new_hash is not None and prev_hash == new_hash:
        return {
            "verdict": VERDICT_PASS,
            "block_reasons": [],
            "review_reasons": [],
            "hash_equal": True,
            "compliance_diff": {},
            "shipping_diff": {},
            "banned_words_diff": {},
            "cost_fields_diff": {},
        }

    # --- truncated / partial projection check → BLOCK ---
    new_partial = _is_partial_projection(new_dims)
    prev_partial = _is_partial_projection(prev_dims)
    if new_partial:
        block_reasons.append(
            "new_dims is a partial/truncated projection — missing required dimension keys. "
            f"Present keys: {sorted(new_dims.keys()) if isinstance(new_dims, dict) else repr(new_dims)}"
        )
    if prev_partial:
        block_reasons.append(
            "prev_dims is a partial/truncated projection — missing required dimension keys. "
            f"Present keys: {sorted(prev_dims.keys()) if isinstance(prev_dims, dict) else repr(prev_dims)}"
        )

    # --- if either side is partial we can't diff reliably → return BLOCK immediately ---
    if block_reasons:
        return {
            "verdict": VERDICT_BLOCK,
            "block_reasons": block_reasons,
            "review_reasons": [],
            "hash_equal": False,
            "compliance_diff": {},
            "shipping_diff": {},
            "banned_words_diff": {},
            "cost_fields_diff": {},
        }

    # --- dimension diffs ---
    compliance_diff = _diff_compliance(
        new_dims["compliance_fields"],
        prev_dims["compliance_fields"],
    )
    shipping_diff = _diff_shipping(
        new_dims["shipping_slab"],
        prev_dims["shipping_slab"],
    )
    banned_diff = _diff_banned_words(
        new_dims["banned_words"],
        prev_dims["banned_words"],
    )
    cost_diff = _diff_cost_fields(
        new_dims["cost_fields"],
        prev_dims["cost_fields"],
    )

    # --- BLOCK threshold checks ---
    req_added_count = len(compliance_diff["required_added"])
    req_removed_count = len(compliance_diff["required_removed"])
    if req_added_count > BLOCK_THRESHOLD_COMPLIANCE_ADDED:
        block_reasons.append(
            f"compliance required_added count {req_added_count} exceeds "
            f"BLOCK_THRESHOLD_COMPLIANCE_ADDED={BLOCK_THRESHOLD_COMPLIANCE_ADDED}"
        )
    if req_removed_count > BLOCK_THRESHOLD_COMPLIANCE_REMOVED:
        block_reasons.append(
            f"compliance required_removed count {req_removed_count} exceeds "
            f"BLOCK_THRESHOLD_COMPLIANCE_REMOVED={BLOCK_THRESHOLD_COMPLIANCE_REMOVED}"
        )

    ship_delta_abs = abs(shipping_diff["shipping_delta"])
    if ship_delta_abs > BLOCK_THRESHOLD_SHIPPING_DELTA_INR:
        block_reasons.append(
            f"shipping_charges delta ₹{ship_delta_abs} exceeds "
            f"BLOCK_THRESHOLD_SHIPPING_DELTA_INR={BLOCK_THRESHOLD_SHIPPING_DELTA_INR}"
        )

    total_banned_added = sum(
        len(v["added"]) for v in banned_diff["per_key"].values()
    )
    if total_banned_added > BLOCK_THRESHOLD_BANNED_ADDED:
        block_reasons.append(
            f"banned_words total added count {total_banned_added} exceeds "
            f"BLOCK_THRESHOLD_BANNED_ADDED={BLOCK_THRESHOLD_BANNED_ADDED}"
        )

    tp_delta_abs = abs(cost_diff["transfer_price_delta"])
    if tp_delta_abs > BLOCK_THRESHOLD_COST_DELTA_INR:
        block_reasons.append(
            f"transfer_price delta ₹{tp_delta_abs} exceeds "
            f"BLOCK_THRESHOLD_COST_DELTA_INR={BLOCK_THRESHOLD_COST_DELTA_INR}"
        )

    # --- REVIEW_REQUIRED: any drift below BLOCK thresholds ---
    if not block_reasons:
        if compliance_diff["changed"]:
            review_reasons.append("compliance_fields changed")
        if shipping_diff["changed"]:
            review_reasons.append("shipping_slab changed")
        if banned_diff["changed"]:
            review_reasons.append("banned_words changed")
        if cost_diff["changed"]:
            review_reasons.append("cost_fields changed")

    # --- Final verdict (BLOCK > REVIEW_REQUIRED > PASS) ---
    if block_reasons:
        verdict = VERDICT_BLOCK
    elif review_reasons:
        verdict = VERDICT_REVIEW
    else:
        verdict = VERDICT_PASS

    return {
        "verdict": verdict,
        "block_reasons": block_reasons,
        "review_reasons": review_reasons,
        "hash_equal": False,
        "compliance_diff": compliance_diff,
        "shipping_diff": shipping_diff,
        "banned_words_diff": banned_diff,
        "cost_fields_diff": cost_diff,
    }


# ---------------------------------------------------------------------------
# Markdown report renderer (mirrors diff_pricing_lookup.render_drift_report)
# ---------------------------------------------------------------------------


def render_diff_report(result: dict[str, Any], run_date: str | None = None) -> str:
    """Render a human-readable markdown diff report.

    Suitable for writing to a .md file or pasting into a PR body.
    Mirrors the structure of diff_pricing_lookup.render_drift_report().

    Args:
        result:   The dict returned by diff_category_snapshot().
        run_date: ISO date string (defaults to today UTC).

    Returns:
        Markdown string.
    """
    if run_date is None:
        run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines: list[str] = [
        f"# Category Rule Diff Report — {run_date}",
        "",
        f"**Verdict:** `{result['verdict']}`",
        f"**Hash-equal short-circuit:** {result.get('hash_equal', False)}",
        "",
    ]

    if result.get("block_reasons"):
        lines += ["## BLOCK reasons", ""]
        for r in result["block_reasons"]:
            lines.append(f"- {r}")
        lines.append("")

    if result.get("review_reasons"):
        lines += ["## Review reasons", ""]
        for r in result["review_reasons"]:
            lines.append(f"- {r}")
        lines.append("")

    # compliance_fields
    cd = result.get("compliance_diff", {})
    if cd.get("changed"):
        lines += ["## compliance_fields changes", ""]
        if cd.get("required_added"):
            lines.append(f"**Required fields ADDED ({len(cd['required_added'])}):**")
            for f in cd["required_added"]:
                lines.append(f"  - `{f}`")
            lines.append("")
        if cd.get("required_removed"):
            lines.append(f"**Required fields REMOVED ({len(cd['required_removed'])}):**")
            for f in cd["required_removed"]:
                lines.append(f"  - `{f}`")
            lines.append("")
        if cd.get("optional_added"):
            lines.append(f"**Optional fields ADDED ({len(cd['optional_added'])}):**")
            for f in cd["optional_added"]:
                lines.append(f"  - `{f}`")
            lines.append("")
        if cd.get("optional_removed"):
            lines.append(f"**Optional fields REMOVED ({len(cd['optional_removed'])}):**")
            for f in cd["optional_removed"]:
                lines.append(f"  - `{f}`")
            lines.append("")

    # shipping_slab
    sd = result.get("shipping_diff", {})
    if sd.get("changed"):
        lines += [
            "## shipping_slab changes",
            "",
            (
                "| field | old | new | delta |"
            ),
            "|-------|-----|-----|-------|",
        ]
        if sd.get("shipping_delta"):
            lines.append(
                f"| shipping_charges | ₹{sd['shipping_charges_old']} | ₹{sd['shipping_charges_new']} "
                f"| {sd['shipping_delta']:+d} |"
            )
        if sd.get("gst_delta"):
            lines.append(
                f"| gst_percentage | {sd['gst_percentage_old']}% | {sd['gst_percentage_new']}% "
                f"| {sd['gst_delta']:+d} |"
            )
        lines.append("")

    # banned_words
    bd = result.get("banned_words_diff", {})
    if bd.get("changed"):
        lines += ["## banned_words changes", ""]
        for key, kd in bd.get("per_key", {}).items():
            if kd.get("changed"):
                lines.append(f"**{key}:**")
                if kd.get("added"):
                    lines.append(f"  Added: {kd['added']}")
                if kd.get("removed"):
                    lines.append(f"  Removed: {kd['removed']}")
                lines.append("")

    # cost_fields
    cfd = result.get("cost_fields_diff", {})
    if cfd.get("changed"):
        lines += ["## cost_fields changes", ""]
        if cfd.get("transfer_price_delta"):
            lines.append(
                f"- transfer_price: ₹{cfd['transfer_price_old']} → ₹{cfd['transfer_price_new']} "
                f"(delta: {cfd['transfer_price_delta']:+.4f})"
            )
        if cfd.get("platform_fee_delta"):
            lines.append(
                f"- platform_fee: ₹{cfd['platform_fee_old']} → ₹{cfd['platform_fee_new']} "
                f"(delta: {cfd['platform_fee_delta']:+.4f})"
            )
        lines.append("")

    if result["verdict"] == VERDICT_PASS:
        lines += [
            "## Result",
            "",
            "Zero drift detected. The category rule surface is unchanged. "
            "No fan-out notification will be triggered.",
            "",
        ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# File-level entry point
# ---------------------------------------------------------------------------


def run_diff(
    new_path: Path,
    prev_path: Path,
    new_hash: str | None = None,
    prev_hash: str | None = None,
    report_dir: Path | None = None,
) -> dict[str, Any]:
    """Load two snapshot JSON files and run diff_category_snapshot().

    Writes a markdown report to report_dir (defaults to logs/scraper/).
    Returns the summary dict.
    """
    new_dims = json.loads(new_path.read_text(encoding="utf-8"))
    prev_dims = json.loads(prev_path.read_text(encoding="utf-8"))

    result = diff_category_snapshot(
        new_dims,
        prev_dims,
        prev_hash=prev_hash,
        new_hash=new_hash,
    )

    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report = render_diff_report(result, run_date=run_date)

    if report_dir is None:
        # Resolve via git common-dir so this works in worktrees
        import subprocess

        _script_dir = Path(__file__).resolve().parent
        try:
            common_dir = subprocess.check_output(
                ["git", "rev-parse", "--git-common-dir"],
                cwd=_script_dir,
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            common_path = Path(common_dir)
            if not common_path.is_absolute():
                common_path = (_script_dir / common_path).resolve()
            report_dir = common_path.parent / "logs" / "scraper"
        except Exception:  # noqa: BLE001
            report_dir = _script_dir.parent.parent.parent / "logs" / "scraper"

    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"category_rules_drift_{run_date}.md"
    report_path.write_text(report, encoding="utf-8")

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Diff two category rule snapshot JSON files."
    )
    parser.add_argument("new_snapshot", help="Path to new snapshot JSON file")
    parser.add_argument("prev_snapshot", help="Path to previous snapshot JSON file")
    parser.add_argument("--new-hash", default=None, help="SHA-256 hex of new snapshot")
    parser.add_argument("--prev-hash", default=None, help="SHA-256 hex of previous snapshot")
    args = parser.parse_args()

    summary = run_diff(
        new_path=Path(args.new_snapshot),
        prev_path=Path(args.prev_snapshot),
        new_hash=args.new_hash,
        prev_hash=args.prev_hash,
    )

    _EXIT = {VERDICT_PASS: 0, VERDICT_REVIEW: 1, VERDICT_BLOCK: 2}
    sys.exit(_EXIT.get(summary["verdict"], 2))
