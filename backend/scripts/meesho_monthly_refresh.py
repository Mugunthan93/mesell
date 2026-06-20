"""meesho_monthly_refresh.py — single monthly entry-point for the MeeSell data refresh.

Sequences three stages in one operator-supervised run:

  Stage A — Category tree + XLSX templates
    Calls meesho_batch_scraper.amain() (existing, unchanged).
    Refreshes backend/app/data/meesho_category_tree.json + data/meesho_templates/.

  Stage B — getTransferPrice census
    Calls meesho_transfer_price_census.run() with the warm storage_state path
    left by any prior authenticated session.  The census reads the freshly-updated
    category tree so it operates on the current leaf set.
    Output: logs/scraper/transfer_price_census.jsonl + _summary.json (gitignored).

  Stage C — Transform + drift gate
    Calls build_pricing_lookup.build() to produce a CANDIDATE lookup file (never
    writes to the committed file directly).
    Then calls diff_pricing_lookup.run_diff() to classify drift vs. the live file.
    Promotion policy:
      PASS            → candidate is staged at logs/scraper/meesho_pricing_lookup.candidate.json;
                        exit 0.  A human opens the data PR and copies the candidate over the
                        committed file (backend/app/data/meesho_pricing_lookup.json) for
                        Data-Lead + founder review before merging.
      REVIEW_REQUIRED → candidate is staged AND a drift report is written to logs/; exit 0.
                        The data PR body MUST include the drift report for review.
      BLOCK           → leave the live file untouched; write the candidate on the side
                        path; exit non-zero; write a STATUS_DATA blocker comment to
                        stderr. Founder reviews before ANY file change.

Idempotency guarantee (§3):
  The committed backend/app/data/meesho_pricing_lookup.json is NEVER overwritten
  in-place by this script under any exit path.  "Staged" means: the candidate is
  written to the gitignored side path (logs/scraper/meesho_pricing_lookup.candidate.json);
  a human promotes it via the reviewed data PR.  The orchestrator's job ends at
  "candidate validated + drift report written + staged for human review."

Exit codes:
  0  — All three stages succeeded; drift verdict is PASS or REVIEW_REQUIRED (candidate
       staged; drift report written when applicable).
  1  — Stage A (batch scraper) failed non-fatally (tree may be partial; Stage B/C skip).
  2  — Stage B (census) failed — OTP required, hard-stop, or gate failure (B summary did
       not pass error_rows==0 / full coverage); Stage C skipped.
  3  — Stage C transform gate failed (build_pricing_lookup validation error).
  4  — Stage C drift gate returned BLOCK; live file untouched; STATUS_DATA blocker written.
  130 — KeyboardInterrupt.

Operator runbook (MUST READ before first live run):
  1. Prerequisites
     a. .meesho_creds.env present (gitignored) with MEESHO_USERNAME / MEESHO_PASSWORD.
        ROTATE credentials before running — they were exposed in prior chat sessions
        (see §7 of W6_REFRESH_SPEC.md).
     b. backend/.venv activated (playwright 1.60+, dotenv, httpx).
     c. WebKit browser installed: playwright install webkit.
     d. logs/scraper/ directory writable (gitignored).
     e. Warm cookies: run while logs/scraper/meesho_storage_state.json is recent
        (from a prior run within the same day) to avoid OTP.  If cookies are cold,
        have the OTP SMS code ready — but note the census script halts on OTP rather
        than waiting; you must re-run with warm cookies or complete OTP manually.

  2. Running
     cd /Users/mugunthansrinivasan/Project/mesell
     backend/.venv/bin/python backend/scripts/meesho_monthly_refresh.py

     Or via the trigger script (which meesho_scrape_trigger.sh now points to):
     bash backend/scripts/meesho_scrape_trigger.sh

  3. Outputs (all gitignored in logs/)
     logs/scraper/transfer_price_census.jsonl        — incremental census (resumable)
     logs/scraper/transfer_price_census_summary.json — census summary (Stage B output)
     logs/scraper/meesho_pricing_lookup.candidate.json — candidate lookup (Stage C)
     logs/scraper/pricing_lookup_drift_<date>.md     — drift report (REVIEW/BLOCK only)
     logs/scraper/meesho_storage_state.json          — warm session cookies

  4. After a PASS or REVIEW_REQUIRED run
     - The candidate is staged at logs/scraper/meesho_pricing_lookup.candidate.json.
     - Open a data PR: manually copy the candidate to backend/app/data/meesho_pricing_lookup.json
       in a dedicated data PR commit, paste the drift report into the PR body
       (REVIEW_REQUIRED runs), and tag the Data-Lead for merge-gate review.
     - The orchestrator NEVER touches backend/app/data/meesho_pricing_lookup.json directly.

  5. After a BLOCK
     - The live file is untouched.
     - Read stderr for the BLOCK reason.
     - Check logs/scraper/pricing_lookup_drift_<date>.md for the full report.
     - Escalate to founder before any file change.

Safety constraints preserved across all stages:
  - getTransferPrice: read-only compute (no listing, no publish, no Submit).
  - Rate: ~1 req / 2.5s on the census endpoint.
  - No OTP: script halts with exit 2 if OTP is required.
  - Resumable census: re-running after a partial Stage B resume is safe.
  - The committed lookup file changes ONLY via the reviewed data PR.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SCRIPT_DIR.parent.parent  # mesell/

LOG_DIR = PROJECT_ROOT / "logs" / "scraper"
CENSUS_SUMMARY_JSON = LOG_DIR / "transfer_price_census_summary.json"
CANDIDATE_PATH = LOG_DIR / "meesho_pricing_lookup.candidate.json"
LIVE_LOOKUP_PATH = _SCRIPT_DIR.parent / "app" / "data" / "meesho_pricing_lookup.json"
STORAGE_STATE_FILE = LOG_DIR / "meesho_storage_state.json"

# The STATUS_DATA file for blocker notes
STATUS_DATA_PATH = PROJECT_ROOT / "docs" / "status" / "STATUS_DATA.md"

# ---------------------------------------------------------------------------
# Lazy imports (all existing modules — no new dependencies)
# ---------------------------------------------------------------------------


def _import_batch_scraper():  # type: ignore[return]
    """Import meesho_batch_scraper from the scripts directory.

    Using an import helper keeps the top-level import section clean and allows
    the module to be imported (e.g. in tests) without Playwright being invoked.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "meesho_batch_scraper",
        _SCRIPT_DIR / "meesho_batch_scraper.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _import_census():  # type: ignore[return]
    """Import meesho_transfer_price_census from the scripts directory."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "meesho_transfer_price_census",
        _SCRIPT_DIR / "meesho_transfer_price_census.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _import_build():  # type: ignore[return]
    """Import build_pricing_lookup from the scripts directory."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "build_pricing_lookup",
        _SCRIPT_DIR / "build_pricing_lookup.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _import_diff():  # type: ignore[return]
    """Import diff_pricing_lookup from the scripts directory."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "diff_pricing_lookup",
        _SCRIPT_DIR / "diff_pricing_lookup.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Logging (minimal — stages configure their own loggers)
# ---------------------------------------------------------------------------
import logging  # noqa: E402  (after imports above to keep module-level clean)

log = logging.getLogger("meesho-monthly-refresh")


def _configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_path = LOG_DIR / f"monthly_refresh_{ts}.log"
    logger = log
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    fh = logging.FileHandler(log_path)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    logger.propagate = False
    log.info("Monthly refresh log: %s", log_path)


# ---------------------------------------------------------------------------
# Stage A — Category tree + XLSX templates
# ---------------------------------------------------------------------------


async def run_stage_a() -> dict:
    """Run Stage A: batch scraper (category tree + XLSX templates).

    Returns:
        {"ok": bool, "storage_state_path": Path | None, "reason": str}
    """
    log.info("=== STAGE A — Category tree + XLSX templates ===")
    try:
        batch_mod = _import_batch_scraper()
        rc = await batch_mod.amain()
        # amain() returns 0 on success, non-zero on error
        if rc != 0:
            log.warning("Stage A finished with return code %d (partial run may be acceptable)", rc)
            return {
                "ok": False,
                "reason": f"meesho_batch_scraper.amain() returned {rc}",
                "storage_state_path": STORAGE_STATE_FILE if STORAGE_STATE_FILE.exists() else None,
            }
        log.info("Stage A complete.")
        return {
            "ok": True,
            "reason": "",
            "storage_state_path": STORAGE_STATE_FILE if STORAGE_STATE_FILE.exists() else None,
        }
    except SystemExit as exc:
        log.error("Stage A raised SystemExit(%s)", exc.code)
        return {"ok": False, "reason": f"SystemExit({exc.code})", "storage_state_path": None}
    except Exception as exc:
        log.exception("Stage A unexpected error: %s", exc)
        return {"ok": False, "reason": str(exc), "storage_state_path": None}


# ---------------------------------------------------------------------------
# Stage B — getTransferPrice census
# ---------------------------------------------------------------------------


async def run_stage_b(storage_state_path: Path | None) -> dict:
    """Run Stage B: getTransferPrice census against the current leaf set.

    Args:
        storage_state_path: Path to a warm Playwright storage state (cookies).
                            Passed through to the census run() so it can avoid
                            a cold login (and the OTP wall).

    Returns:
        {"ok": bool, "reason": str, "summary": dict | None}
        summary is the parsed CENSUS_SUMMARY_JSON when ok=True; None on failure.
    """
    log.info("=== STAGE B — getTransferPrice census ===")
    if storage_state_path:
        log.info("Warm storage_state: %s", storage_state_path)
    else:
        log.info("No warm storage_state available — census will attempt fresh login")

    try:
        census_mod = _import_census()
        await census_mod.run(storage_state_path=storage_state_path)
    except RuntimeError as exc:
        msg = str(exc)
        if "OTP_REQUIRED" in msg:
            log.error("Stage B halted: OTP required. Rerun with warm cookies. %s", msg)
            return {"ok": False, "reason": f"OTP_REQUIRED: {msg}", "summary": None}
        log.error("Stage B RuntimeError: %s", exc)
        return {"ok": False, "reason": msg, "summary": None}
    except SystemExit as exc:
        log.error("Stage B raised SystemExit(%s)", exc.code)
        return {"ok": False, "reason": f"SystemExit({exc.code})", "summary": None}
    except Exception as exc:
        log.exception("Stage B unexpected error: %s", exc)
        return {"ok": False, "reason": str(exc), "summary": None}

    # Read the summary written by the census
    if not CENSUS_SUMMARY_JSON.exists():
        reason = f"Census summary not found at {CENSUS_SUMMARY_JSON} after run"
        log.error(reason)
        return {"ok": False, "reason": reason, "summary": None}

    try:
        with open(CENSUS_SUMMARY_JSON, encoding="utf-8") as fh:
            summary = json.load(fh)
    except Exception as exc:
        reason = f"Could not parse census summary: {exc}"
        log.error(reason)
        return {"ok": False, "reason": reason, "summary": None}

    # Gate check: hard invariants (mirrors §3)
    error_rows = summary.get("error_rows", -1)
    rows_with_data = summary.get("rows_with_data", 0)
    expected = 3772

    if error_rows != 0:
        reason = f"Census error_rows={error_rows} (expected 0)"
        log.error("Stage B gate failed: %s", reason)
        return {"ok": False, "reason": reason, "summary": summary}

    if rows_with_data != expected:
        reason = f"Census rows_with_data={rows_with_data} (expected {expected})"
        log.error("Stage B gate failed: %s", reason)
        return {"ok": False, "reason": reason, "summary": summary}

    log.info(
        "Stage B complete: %d rows, 0 errors, summary at %s",
        rows_with_data,
        CENSUS_SUMMARY_JSON,
    )
    return {"ok": True, "reason": "", "summary": summary}


# ---------------------------------------------------------------------------
# Stage C — Transform + drift gate
# ---------------------------------------------------------------------------


def run_stage_c(census_summary: dict) -> dict:
    """Run Stage C: build the candidate lookup and apply the drift gate.

    Args:
        census_summary: The parsed census summary dict from Stage B (not used directly;
                        Stage C reads CENSUS_SUMMARY_JSON from disk via build()).

    Returns:
        {
            "ok":       bool,
            "verdict":  "PASS" | "REVIEW_REQUIRED" | "BLOCK" | "BUILD_FAIL",
            "reason":   str,
            "candidate_path": Path | None,
            "drift_summary":  dict | None,
        }
    """
    log.info("=== STAGE C — Transform + drift gate ===")

    build_mod = _import_build()
    diff_mod = _import_diff()

    # 3a. Build the candidate (validation gate — never touches the live file)
    CANDIDATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    verdict = build_mod.build(
        census_path=CENSUS_SUMMARY_JSON,
        candidate_out=CANDIDATE_PATH,
    )
    if not verdict["ok"]:
        log.error("Stage C build gate FAILED: %s", verdict["reason"])
        return {
            "ok": False,
            "verdict": "BUILD_FAIL",
            "reason": verdict["reason"],
            "candidate_path": None,
            "drift_summary": None,
        }
    log.info("Stage C build gate PASSED: candidate at %s", CANDIDATE_PATH)

    # 3b. Drift gate — compare candidate vs. live file
    if not LIVE_LOOKUP_PATH.exists():
        # First-time run: no live file to compare against → candidate is staged only.
        # A human copies it into backend/app/data/ via the reviewed data PR.
        log.info(
            "No live lookup file at %s — first-time run; candidate staged at %s. "
            "Copy to %s via the data PR.",
            LIVE_LOOKUP_PATH,
            CANDIDATE_PATH,
            LIVE_LOOKUP_PATH,
        )
        return {
            "ok": True,
            "verdict": "PASS",
            "reason": (
                "First-time run (no live file); candidate staged for human promotion "
                f"via data PR at {CANDIDATE_PATH}"
            ),
            "candidate_path": CANDIDATE_PATH,
            "drift_summary": None,
        }

    # Load seeded leaf IDs from the categories data if available (for removed-seeded BLOCK)
    seeded_leaf_ids: set[str] | None = _load_seeded_leaf_ids()

    drift_summary = diff_mod.run_diff(
        candidate_path=CANDIDATE_PATH,
        live_path=LIVE_LOOKUP_PATH,
        seeded_leaf_ids=seeded_leaf_ids,
        write_report=True,
    )

    drift_verdict = drift_summary["verdict"]
    log.info("Drift gate verdict: %s", drift_verdict)

    if drift_verdict == diff_mod.VERDICT_BLOCK:
        log.error("Stage C drift gate BLOCK: %s", drift_summary.get("block_reasons"))
        _write_status_blocker(drift_summary)
        return {
            "ok": False,
            "verdict": "BLOCK",
            "reason": "; ".join(drift_summary.get("block_reasons", ["unknown block"])),
            "candidate_path": CANDIDATE_PATH,
            "drift_summary": drift_summary,
        }

    # PASS or REVIEW_REQUIRED → candidate is already staged at CANDIDATE_PATH (side path).
    # The orchestrator's job ends here.  A human promotes via the reviewed data PR:
    #   cp logs/scraper/meesho_pricing_lookup.candidate.json \
    #      backend/app/data/meesho_pricing_lookup.json
    # The committed file (LIVE_LOOKUP_PATH) is NEVER written by this script.
    log.info(
        "Candidate staged at %s (verdict=%s). "
        "Promote via data PR — do NOT copy manually outside the review process.",
        CANDIDATE_PATH,
        drift_verdict,
    )

    if drift_verdict == diff_mod.VERDICT_REVIEW:
        log.warning(
            "Drift verdict REVIEW_REQUIRED — paste the drift report into the data PR body "
            "for Data-Lead + founder review before merging."
        )
        log.warning("Block reasons: (none — threshold not exceeded)")
        log.warning("Review reasons: %s", drift_summary.get("review_reasons"))

    return {
        "ok": True,
        "verdict": drift_verdict,
        "reason": "",
        "candidate_path": CANDIDATE_PATH,
        "drift_summary": drift_summary,
    }


def _load_seeded_leaf_ids() -> set[str] | None:
    """Attempt to load the seeded meesho_leaf_ids from the category tree.

    The category tree (meesho_category_tree.json) is the best available proxy for
    the seeded leaf IDs in the categories table — not a DB query, which would
    require a live connection.  If the file is absent, returns None (no BLOCK check
    on removed-seeded leaves).
    """
    tree_path = PROJECT_ROOT / "backend" / "app" / "data" / "meesho_category_tree.json"
    if not tree_path.exists():
        log.warning("Category tree not found at %s — skipping seeded-leaf BLOCK check", tree_path)
        return None
    try:
        with open(tree_path, encoding="utf-8") as fh:
            tree = json.load(fh)
        ids: set[str] = set()
        for cat in tree.get("categories", []):
            lid = cat.get("leaf_id")
            if lid is not None:
                ids.add(str(lid))
        log.info("Loaded %d seeded leaf IDs from category tree for BLOCK check", len(ids))
        return ids
    except Exception as exc:
        log.warning("Could not load seeded leaf IDs: %s", exc)
        return None


def _write_status_blocker(drift_summary: dict) -> None:
    """Append a BLOCK note to STATUS_DATA.md so the data engineer sees it."""
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    block_reasons = drift_summary.get("block_reasons", [])
    block_text = "\n".join(f"  - {r}" for r in block_reasons)
    entry = (
        f"\n\n=== MONTHLY REFRESH BLOCK: {run_date} ===\n"
        f"Drift gate returned BLOCK. Live file NOT updated.\n"
        f"Candidate: {CANDIDATE_PATH}\n"
        f"Block reasons:\n{block_text}\n"
        f"Action: founder / Data-Lead review required before any file change.\n"
        f"=========================================\n"
    )
    try:
        if STATUS_DATA_PATH.exists():
            with open(STATUS_DATA_PATH, "a", encoding="utf-8") as fh:
                fh.write(entry)
            log.info("BLOCK note appended to %s", STATUS_DATA_PATH)
        else:
            log.warning("STATUS_DATA.md not found at %s — BLOCK note not appended", STATUS_DATA_PATH)
        # Always print to stderr so CI / launchd captures it
        print(entry, file=sys.stderr)
    except Exception as exc:
        log.warning("Could not write BLOCK note to STATUS_DATA.md: %s", exc)
        print(entry, file=sys.stderr)


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


async def orchestrate() -> int:
    """Run Stage A → B → C and return a POSIX exit code.

    Exit codes (see module docstring for full table):
      0  PASS or REVIEW_REQUIRED (candidate staged)
      1  Stage A failed
      2  Stage B failed
      3  Stage C build gate failed
      4  Stage C drift gate BLOCK
      130 KeyboardInterrupt
    """
    _configure_logging()
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log.info("=== MeeSell Monthly Refresh — %s ===", run_date)
    log.info("Stages: A (tree+templates) → B (census) → C (transform+drift)")

    # --- Stage A ---
    a_result = await run_stage_a()
    if not a_result["ok"]:
        log.error("Stage A failed: %s — aborting refresh", a_result["reason"])
        print(
            f"\nMONTHLY REFRESH FAILED — Stage A:\n  {a_result['reason']}\n"
            "  Category tree / templates may be partial.  Stage B and C skipped.",
            file=sys.stderr,
        )
        return 1

    # --- Stage B ---
    b_result = await run_stage_b(a_result.get("storage_state_path"))
    if not b_result["ok"]:
        log.error("Stage B failed: %s — aborting refresh", b_result["reason"])
        print(
            f"\nMONTHLY REFRESH FAILED — Stage B (census):\n  {b_result['reason']}\n"
            "  Stage C skipped.  Census is resumable — re-run this script.",
            file=sys.stderr,
        )
        return 2

    # --- Stage C ---
    c_result = run_stage_c(b_result["summary"])
    if not c_result["ok"]:
        verdict = c_result["verdict"]
        if verdict == "BLOCK":
            log.error("Stage C BLOCK: %s", c_result["reason"])
            print(
                f"\nMONTHLY REFRESH BLOCKED — Drift gate:\n  {c_result['reason']}\n"
                f"  Candidate is at: {c_result['candidate_path']}\n"
                "  Live file is untouched.\n"
                "  See STATUS_DATA.md and the drift report in logs/scraper/.",
                file=sys.stderr,
            )
            return 4
        # BUILD_FAIL or other
        log.error("Stage C failed (%s): %s", verdict, c_result["reason"])
        print(
            f"\nMONTHLY REFRESH FAILED — Stage C ({verdict}):\n  {c_result['reason']}",
            file=sys.stderr,
        )
        return 3

    # Success
    final_verdict = c_result["verdict"]
    log.info("=== Monthly refresh COMPLETE — verdict: %s ===", final_verdict)

    drift = c_result.get("drift_summary") or {}
    print(
        f"\n=== MONTHLY REFRESH COMPLETE ===\n"
        f"Drift verdict:     {final_verdict}\n"
        f"Candidate staged:  {c_result['candidate_path']}\n"
        f"Live file:         UNTOUCHED ({LIVE_LOOKUP_PATH})\n"
        f"Next step:         open a data PR, copy the candidate into\n"
        f"                   backend/app/data/meesho_pricing_lookup.json,\n"
        f"                   and tag the Data-Lead for merge-gate review.\n"
        f"Added sscat_ids:   {len(drift.get('added', []))}\n"
        f"Removed sscat_ids: {len(drift.get('removed', []))}\n"
        f"Shipping changes:  {len(drift.get('shipping_changed', []))}\n"
        f"Unchanged rows:    {drift.get('unchanged_count', 'n/a')}\n"
    )
    if final_verdict == "REVIEW_REQUIRED":
        print(
            "ACTION REQUIRED: drift detected.  Paste the drift report from\n"
            "  logs/scraper/pricing_lookup_drift_<date>.md\n"
            "into the data PR body for Data-Lead + founder review before merging.",
            file=sys.stderr,
        )
    return 0


def main() -> int:
    try:
        return asyncio.run(orchestrate())
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
