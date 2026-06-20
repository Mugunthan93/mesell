"""diff_pricing_lookup.py — drift detector for monthly pricing lookup refreshes.

Compares a CANDIDATE meesho_pricing_lookup.json (produced by build_pricing_lookup.py
--candidate-out) against the COMMITTED live file and emits:
  - A machine-readable summary dict (returned by diff_lookups())
  - A human-readable markdown report written to logs/scraper/pricing_lookup_drift_<date>.md
    (gitignored)

IMPORTANT: only the ``lookup`` payload is compared.  ``_meta.generated_at`` legitimately
changes on every run and is intentionally excluded from the diff — a no-change month
produces an EMPTY drift report and a byte-identical ``lookup`` payload.

Promotion policy (caller enforces; this module only classifies):
  PASS           — zero drift; auto-promotable
  REVIEW_REQUIRED — any added / removed / shipping-changed row within numeric thresholds;
                   caller MUST paste the drift report into the PR for Data-Lead review
  BLOCK          — commission_percentage != 0 on ANY row, OR a removed sscat_id is still
                   present in the seeded meesho_leaf_id set, OR drift exceeds a hard
                   numeric threshold

FOUNDER-OVERRIDABLE DEFAULTS (clearly marked at module level):
  Tune these before the first live monthly run if needed.
  Setting a threshold to 0 turns any non-zero drift for that dimension into a BLOCK.

Stdlib-only. No new dependencies.

CLI usage (operator / debugging):
  python backend/scripts/diff_pricing_lookup.py [CANDIDATE_PATH] [LIVE_PATH]
          [--seed-ids ID1 ID2 ...]
  Exit codes: 0 = PASS, 1 = REVIEW_REQUIRED, 2 = BLOCK.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# FOUNDER-OVERRIDABLE DEFAULTS
# These constants set the boundaries between PASS / REVIEW_REQUIRED / BLOCK.
# Setting a constant to 0 turns any non-zero drift into a BLOCK for that dimension.
# ---------------------------------------------------------------------------

# Maximum number of newly-ADDED sscat_ids before the result escalates to BLOCK.
# Default: any number of added leaves is REVIEW_REQUIRED (never blocked purely on count).
BLOCK_THRESHOLD_ADDED: int = 9999  # FOUNDER-OVERRIDABLE DEFAULT

# Maximum number of REMOVED sscat_ids before the result escalates to BLOCK.
# A removed sscat_id still in the seeded categories table is ALWAYS BLOCK regardless.
BLOCK_THRESHOLD_REMOVED: int = 9999  # FOUNDER-OVERRIDABLE DEFAULT

# Maximum absolute shipping delta (₹) for a single row before the whole run is BLOCK.
# Default: any shipping change triggers REVIEW_REQUIRED (never blocked on amount alone).
BLOCK_THRESHOLD_SHIPPING_DELTA_INR: int = 9999  # FOUNDER-OVERRIDABLE DEFAULT

# Maximum number of shipping-changed rows before BLOCK.
# Default: any shipping change is REVIEW_REQUIRED (never blocked on row count alone).
BLOCK_THRESHOLD_SHIPPING_CHANGED: int = 9999  # FOUNDER-OVERRIDABLE DEFAULT

# ---------------------------------------------------------------------------
# Verdict strings (stable interface for callers)
# ---------------------------------------------------------------------------
VERDICT_PASS = "PASS"
VERDICT_REVIEW = "REVIEW_REQUIRED"
VERDICT_BLOCK = "BLOCK"

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent


def _default_live_path() -> Path:
    """Shipped production lookup committed in the repo."""
    return _SCRIPT_DIR.parent / "app" / "data" / "meesho_pricing_lookup.json"


def _default_log_dir() -> Path:
    """Drift reports go to logs/scraper/ which is gitignored.

    Resolves the primary checkout root via ``git rev-parse --git-common-dir``
    so this works correctly whether called from the primary checkout or a worktree.
    """
    try:
        common_dir = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=_SCRIPT_DIR,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        common_path = Path(common_dir)
        if not common_path.is_absolute():
            common_path = (_SCRIPT_DIR / common_path).resolve()
        return common_path.parent / "logs" / "scraper"
    except Exception:
        return _SCRIPT_DIR.parent.parent.parent / "logs" / "scraper"


# ---------------------------------------------------------------------------
# Core diff logic
# ---------------------------------------------------------------------------


def diff_lookups(
    candidate: dict[str, Any],
    live: dict[str, Any],
    seeded_leaf_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Compare the ``lookup`` payloads of two meesho_pricing_lookup documents.

    Args:
        candidate:        Parsed JSON of the candidate file (the new version).
        live:             Parsed JSON of the committed/live file.
        seeded_leaf_ids:  Optional set of sscat_id strings seeded in ``categories``
                          (meesho_leaf_id column).  When provided, any removed
                          sscat_id still present in this set forces BLOCK.

    Returns:
        A summary dict with the following shape::

            {
                "verdict":            "PASS" | "REVIEW_REQUIRED" | "BLOCK",
                "block_reasons":      [...],   # empty list when not BLOCK
                "review_reasons":     [...],   # empty list when PASS
                "added":              [...],   # new sscat_id strings
                "removed":            [...],   # removed sscat_id strings
                "shipping_changed":   [        # rows where shipping differed
                    {
                        "sscat_id": str,
                        "old":      int,
                        "new":      int,
                        "delta":    int,   # new - old (signed)
                        "pct":      float, # signed percentage change
                    },
                    ...
                ],
                "commission_nonzero": [...],   # sscat_ids with commission != 0
                "unchanged_count":    int,
                "total_candidate":    int,
                "total_live":         int,
            }

    The caller (meesho_monthly_refresh.py) enforces the promotion policy based on
    ``verdict``.  This function only detects and classifies — it does NOT write
    any file and does NOT promote the candidate.
    """
    # Extract lookup dicts.  ``_meta`` (including generated_at) is intentionally ignored.
    cand_lookup: dict[str, dict] = candidate.get("lookup", {})
    live_lookup: dict[str, dict] = live.get("lookup", {})

    cand_ids = set(cand_lookup.keys())
    live_ids = set(live_lookup.keys())

    added: list[str] = sorted(cand_ids - live_ids)
    removed: list[str] = sorted(live_ids - cand_ids)
    common: set[str] = cand_ids & live_ids

    # Per-row analysis on the common set
    shipping_changed: list[dict] = []
    unchanged_count: int = 0
    commission_nonzero: list[str] = []

    for sscat_id in sorted(common):
        c_row = cand_lookup[sscat_id]
        l_row = live_lookup[sscat_id]

        c_ship = int(c_row.get("shipping_charges", 0))
        l_ship = int(l_row.get("shipping_charges", 0))

        # Commission must be 0 in the candidate
        c_comm = float(c_row.get("commission_percentage", 0))
        if c_comm != 0.0:
            commission_nonzero.append(sscat_id)

        if c_ship != l_ship:
            delta = c_ship - l_ship
            pct = round((delta / l_ship) * 100, 2) if l_ship != 0 else float("inf")
            shipping_changed.append(
                {
                    "sscat_id": sscat_id,
                    "old": l_ship,
                    "new": c_ship,
                    "delta": delta,
                    "pct": pct,
                }
            )
        else:
            unchanged_count += 1

    # Check commission on purely added rows too
    for sscat_id in added:
        c_row = cand_lookup[sscat_id]
        c_comm = float(c_row.get("commission_percentage", 0))
        if c_comm != 0.0:
            commission_nonzero.append(sscat_id)

    # Detect removed ids that are still seeded in the categories table
    seeded_ids_norm = {str(sid) for sid in seeded_leaf_ids} if seeded_leaf_ids else set()
    removed_and_seeded: list[str] = sorted(set(removed) & seeded_ids_norm)

    # -----------------------------------------------------------------------
    # Verdict logic — BLOCK trumps REVIEW_REQUIRED; both trump PASS
    # -----------------------------------------------------------------------
    block_reasons: list[str] = []
    review_reasons: list[str] = []

    # Hard BLOCK conditions
    if commission_nonzero:
        block_reasons.append(
            f"commission_percentage != 0 on {len(commission_nonzero)} row(s): "
            f"{commission_nonzero[:5]}{'...' if len(commission_nonzero) > 5 else ''}"
        )
    if removed_and_seeded:
        block_reasons.append(
            f"{len(removed_and_seeded)} removed sscat_id(s) are still seeded in "
            f"categories: "
            f"{removed_and_seeded[:10]}{'...' if len(removed_and_seeded) > 10 else ''}"
        )
    if len(added) > BLOCK_THRESHOLD_ADDED:
        block_reasons.append(
            f"added count {len(added)} exceeds BLOCK_THRESHOLD_ADDED={BLOCK_THRESHOLD_ADDED}"
        )
    if len(removed) > BLOCK_THRESHOLD_REMOVED:
        block_reasons.append(
            f"removed count {len(removed)} exceeds "
            f"BLOCK_THRESHOLD_REMOVED={BLOCK_THRESHOLD_REMOVED}"
        )
    if len(shipping_changed) > BLOCK_THRESHOLD_SHIPPING_CHANGED:
        block_reasons.append(
            f"shipping_changed count {len(shipping_changed)} exceeds "
            f"BLOCK_THRESHOLD_SHIPPING_CHANGED={BLOCK_THRESHOLD_SHIPPING_CHANGED}"
        )
    if shipping_changed:
        max_delta = max(abs(r["delta"]) for r in shipping_changed)
        if max_delta > BLOCK_THRESHOLD_SHIPPING_DELTA_INR:
            block_reasons.append(
                f"max shipping delta ₹{max_delta} exceeds "
                f"BLOCK_THRESHOLD_SHIPPING_DELTA_INR={BLOCK_THRESHOLD_SHIPPING_DELTA_INR}"
            )

    # REVIEW_REQUIRED: any drift that didn't trigger a BLOCK
    if not block_reasons:
        if added:
            review_reasons.append(f"{len(added)} new sscat_id(s) added")
        if removed:
            review_reasons.append(f"{len(removed)} sscat_id(s) removed")
        if shipping_changed:
            review_reasons.append(f"{len(shipping_changed)} row(s) have shipping changes")

    # Final verdict
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
        "added": added,
        "removed": removed,
        "shipping_changed": shipping_changed,
        "commission_nonzero": commission_nonzero,
        "unchanged_count": unchanged_count,
        "total_candidate": len(cand_lookup),
        "total_live": len(live_lookup),
    }


# ---------------------------------------------------------------------------
# Markdown report renderer
# ---------------------------------------------------------------------------


def render_drift_report(summary: dict[str, Any], run_date: str | None = None) -> str:
    """Render a human-readable markdown drift report from a diff_lookups() summary.

    Args:
        summary:  The dict returned by diff_lookups().
        run_date: ISO date string for the report header (defaults to today UTC).

    Returns:
        Markdown string ready to write to a .md file or paste into a PR body.
    """
    if run_date is None:
        run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines: list[str] = [
        f"# Pricing Lookup Drift Report — {run_date}",
        "",
        f"**Verdict:** `{summary['verdict']}`",
        (
            f"**Candidate rows:** {summary['total_candidate']}  |  "
            f"**Live rows:** {summary['total_live']}"
        ),
        (
            f"**Added:** {len(summary['added'])}  |  "
            f"**Removed:** {len(summary['removed'])}  |  "
            f"**Shipping changed:** {len(summary['shipping_changed'])}  |  "
            f"**Unchanged:** {summary['unchanged_count']}"
        ),
        "",
    ]

    if summary["block_reasons"]:
        lines += ["## BLOCK reasons", ""]
        for r in summary["block_reasons"]:
            lines.append(f"- {r}")
        lines.append("")

    if summary["review_reasons"]:
        lines += ["## Review reasons", ""]
        for r in summary["review_reasons"]:
            lines.append(f"- {r}")
        lines.append("")

    if summary["added"]:
        lines += [f"## Added sscat_ids ({len(summary['added'])})", ""]
        for sid in summary["added"][:50]:
            lines.append(f"- `{sid}`")
        if len(summary["added"]) > 50:
            lines.append(f"- … and {len(summary['added']) - 50} more")
        lines.append("")

    if summary["removed"]:
        lines += [f"## Removed sscat_ids ({len(summary['removed'])})", ""]
        for sid in summary["removed"][:50]:
            lines.append(f"- `{sid}`")
        if len(summary["removed"]) > 50:
            lines.append(f"- … and {len(summary['removed']) - 50} more")
        lines.append("")

    if summary["shipping_changed"]:
        lines += [
            f"## Shipping changes ({len(summary['shipping_changed'])} rows)",
            "",
            "| sscat_id | old ₹ | new ₹ | delta ₹ | pct % |",
            "|----------|-------|-------|---------|-------|",
        ]
        for row in summary["shipping_changed"][:100]:
            lines.append(
                f"| `{row['sscat_id']}` | {row['old']} | {row['new']} "
                f"| {row['delta']:+d} | {row['pct']:+.2f} |"
            )
        if len(summary["shipping_changed"]) > 100:
            lines.append(
                f"\n_… and {len(summary['shipping_changed']) - 100} more rows truncated._"
            )
        lines.append("")

    if summary["commission_nonzero"]:
        lines += [
            f"## ALERT: Non-zero commission rows ({len(summary['commission_nonzero'])})",
            "",
        ]
        for sid in summary["commission_nonzero"][:20]:
            lines.append(f"- `{sid}`")
        lines.append("")

    if summary["verdict"] == VERDICT_PASS:
        lines += [
            "## Result",
            "",
            "Zero drift detected. The candidate `lookup` payload is byte-identical to "
            "the committed file (ignoring `_meta.generated_at`). Auto-promotable.",
            "",
        ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# File-level entry point (load files, diff, optionally write report)
# ---------------------------------------------------------------------------


def run_diff(
    candidate_path: Path,
    live_path: Path | None = None,
    seeded_leaf_ids: set[str] | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    """Load both lookup files, diff them, optionally write the markdown report.

    Args:
        candidate_path:   Path to the candidate JSON produced by
                          ``build_pricing_lookup.py --candidate-out``.
        live_path:        Path to the committed lookup JSON.
                          Defaults to the shipped ``meesho_pricing_lookup.json``.
        seeded_leaf_ids:  Optional set of seeded leaf id strings for BLOCK detection.
        write_report:     When True (default), write a markdown report to
                          ``logs/scraper/pricing_lookup_drift_<date>.md`` (gitignored).

    Returns:
        The summary dict from diff_lookups().
    """
    if live_path is None:
        live_path = _default_live_path()

    with candidate_path.open(encoding="utf-8") as fh:
        candidate = json.load(fh)
    with live_path.open(encoding="utf-8") as fh:
        live = json.load(fh)

    summary = diff_lookups(candidate, live, seeded_leaf_ids=seeded_leaf_ids)

    if write_report:
        run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        report_text = render_drift_report(summary, run_date=run_date)
        log_dir = _default_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        report_path = log_dir / f"pricing_lookup_drift_{run_date}.md"
        report_path.write_text(report_text, encoding="utf-8")
        print(f"Drift report written to {report_path}", file=sys.stderr)

    return summary


# ---------------------------------------------------------------------------
# CLI shim
# ---------------------------------------------------------------------------


def _cli() -> None:
    """Minimal CLI for operator / debugging use.

    Usage::

      python backend/scripts/diff_pricing_lookup.py [CANDIDATE_PATH] [LIVE_PATH]
              [--seed-ids ID1 ID2 ...]

    Exit codes: 0 = PASS, 1 = REVIEW_REQUIRED, 2 = BLOCK.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Diff two meesho_pricing_lookup.json files and report drift."
    )
    parser.add_argument(
        "candidate",
        nargs="?",
        help=(
            "Path to the candidate JSON "
            "(default: logs/scraper/meesho_pricing_lookup.candidate.json)"
        ),
    )
    parser.add_argument(
        "live",
        nargs="?",
        help=(
            "Path to the live/committed JSON "
            "(default: backend/app/data/meesho_pricing_lookup.json)"
        ),
    )
    parser.add_argument(
        "--seed-ids",
        nargs="*",
        default=None,
        metavar="ID",
        help="Space-separated seeded meesho_leaf_id values to check for removed-but-seeded.",
    )
    args = parser.parse_args()

    if args.candidate:
        candidate_path = Path(args.candidate)
    else:
        log_dir = _default_log_dir()
        candidate_path = log_dir / "meesho_pricing_lookup.candidate.json"

    live_path: Path | None = Path(args.live) if args.live else None
    seeded_leaf_ids: set[str] | None = (
        set(args.seed_ids) if args.seed_ids is not None else None
    )

    summary = run_diff(candidate_path, live_path, seeded_leaf_ids=seeded_leaf_ids)

    # Machine-readable JSON to stdout; the markdown report already went to logs/
    print(json.dumps(summary, indent=2))

    if summary["verdict"] == VERDICT_BLOCK:
        sys.exit(2)
    elif summary["verdict"] == VERDICT_REVIEW:
        sys.exit(1)
    # PASS → exit 0


if __name__ == "__main__":
    _cli()
