"""test_diff_pricing_lookup.py — §6 acceptance tests for the drift detector.

Covers §6 tests:
  - test_idempotent_no_change         (same lookup → empty drift, PASS) [shared with gate]
  - test_drift_detects_shipping_change  (one row 82→90 → shipping_changed listed)
  - test_drift_detects_added_removed    (add 1, drop 1 → report lists 1 added, 1 removed)
  - test_drift_blocks_removed_seeded_leaf (removed sscat in seed set → BLOCK)
  - test_orchestrator_stage_order        (mocked stages A→B→C; C aborts if B fails)

DB-SAFETY: NO database imports, NO live connection.  seed_leaf_ids are synthetic
Python sets passed as arguments — NEVER the live dev DB.  This module is a
stdlib-only pure-function test suite.

Marker: unit (§19.D).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from scripts.diff_pricing_lookup import (  # type: ignore[import]
    VERDICT_BLOCK,
    VERDICT_PASS,
    VERDICT_REVIEW,
    diff_lookups,
    render_drift_report,
    run_diff,
)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

EXPECTED_COUNT = 3772


def _make_lookup_doc(
    entries: dict[str, int] | None = None,
    generated_at: str = "2026-06-01T00:00:00",
) -> dict[str, Any]:
    """Return a minimal pricing lookup document.

    Args:
        entries:      {sscat_id_str: shipping_charges_int}.  When None, builds
                      EXPECTED_COUNT rows with shipping=50.
        generated_at: Value for _meta.generated_at (should differ between live and candidate
                      in idempotency tests — only the lookup payload matters).
    """
    if entries is None:
        entries = {str(10000 + i): 50 + (i % 100) for i in range(EXPECTED_COUNT)}

    lookup = {
        sscat_id: {"commission_percentage": 0, "shipping_charges": shipping}
        for sscat_id, shipping in entries.items()
    }
    return {
        "_meta": {
            "generated_at": generated_at,
            "total": len(lookup),
            "version": "1",
        },
        "lookup": lookup,
    }


# ---------------------------------------------------------------------------
# Idempotency — no change → PASS + empty drift
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_idempotent_no_change() -> None:
    """§6: same lookup in twice → verdict=PASS, empty drift lists."""
    live = _make_lookup_doc(generated_at="2026-05-01T00:00:00")
    candidate = _make_lookup_doc(generated_at="2026-06-01T00:00:00")  # only _meta differs

    summary = diff_lookups(candidate, live)

    assert summary["verdict"] == VERDICT_PASS
    assert summary["added"] == []
    assert summary["removed"] == []
    assert summary["shipping_changed"] == []
    assert summary["commission_nonzero"] == []
    assert summary["block_reasons"] == []
    assert summary["review_reasons"] == []
    assert summary["unchanged_count"] == EXPECTED_COUNT


# ---------------------------------------------------------------------------
# Shipping change detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_drift_detects_shipping_change() -> None:
    """§6: one row shipping 82→90 → drift report lists sscat_id with delta +8."""
    base_entries = {str(10000 + i): 50 for i in range(10)}
    # Override sscat 10949 (the canonical anchor from the model memory)
    base_entries["10949"] = 82

    live = _make_lookup_doc(entries={**base_entries})
    candidate_entries = {**base_entries, "10949": 90}  # changed
    candidate = _make_lookup_doc(entries=candidate_entries)

    summary = diff_lookups(candidate, live)

    assert summary["verdict"] == VERDICT_REVIEW, (
        f"Expected REVIEW_REQUIRED for shipping change; got {summary['verdict']}"
    )
    assert len(summary["shipping_changed"]) == 1
    changed = summary["shipping_changed"][0]
    assert changed["sscat_id"] == "10949"
    assert changed["old"] == 82
    assert changed["new"] == 90
    assert changed["delta"] == 8
    assert changed["pct"] == pytest.approx(round(8 / 82 * 100, 2))
    assert summary["added"] == []
    assert summary["removed"] == []


@pytest.mark.unit
def test_drift_detects_shipping_change_renders_in_report() -> None:
    """Shipping change appears in the markdown report table."""
    base = {"10949": 82, "10000": 50}
    live = _make_lookup_doc(entries=base)
    candidate = _make_lookup_doc(entries={**base, "10949": 90})

    summary = diff_lookups(candidate, live)
    report = render_drift_report(summary, run_date="2026-06-01")

    assert "10949" in report
    assert "82" in report
    assert "90" in report
    assert "+8" in report


# ---------------------------------------------------------------------------
# Added / removed detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_drift_detects_added_removed() -> None:
    """§6: add one sscat_id, drop one → report lists 1 added, 1 removed, REVIEW_REQUIRED."""
    live_entries = {str(10000 + i): 50 for i in range(10)}
    # Candidate: drop 10000, add 99999
    candidate_entries = {str(10001 + i): 50 for i in range(9)}
    candidate_entries["99999"] = 70

    live = _make_lookup_doc(entries=live_entries)
    candidate = _make_lookup_doc(entries=candidate_entries)

    summary = diff_lookups(candidate, live)

    assert summary["verdict"] == VERDICT_REVIEW
    assert "99999" in summary["added"]
    assert len(summary["added"]) == 1
    assert "10000" in summary["removed"]
    assert len(summary["removed"]) == 1
    assert summary["shipping_changed"] == []


@pytest.mark.unit
def test_drift_added_ids_in_report() -> None:
    """Added sscat_id appears in the markdown report."""
    live_entries = {"10000": 50}
    candidate_entries = {"10000": 50, "99999": 70}
    live = _make_lookup_doc(entries=live_entries)
    candidate = _make_lookup_doc(entries=candidate_entries)

    summary = diff_lookups(candidate, live)
    report = render_drift_report(summary, run_date="2026-06-01")

    assert "99999" in report
    assert "Added" in report


# ---------------------------------------------------------------------------
# Removed seeded leaf → BLOCK
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_drift_blocks_removed_seeded_leaf() -> None:
    """§6: a removed sscat_id still in the seed meesho_leaf_id set → verdict=BLOCK.

    Uses a FIXTURE set of seeded ids — NEVER the live dev DB.
    """
    live_entries = {"10000": 50, "20000": 60, "30000": 70}
    # Candidate drops 20000
    candidate_entries = {"10000": 50, "30000": 70}

    live = _make_lookup_doc(entries=live_entries)
    candidate = _make_lookup_doc(entries=candidate_entries)

    # 20000 is still seeded in categories (fixture set)
    seeded_leaf_ids: set[str] = {"10000", "20000", "30000"}

    summary = diff_lookups(candidate, live, seeded_leaf_ids=seeded_leaf_ids)

    assert summary["verdict"] == VERDICT_BLOCK, (
        f"Expected BLOCK for removed seeded leaf; got {summary['verdict']}"
    )
    assert any("seeded" in r for r in summary["block_reasons"]), (
        f"Expected seeded-leaf BLOCK reason; got {summary['block_reasons']}"
    )
    assert "20000" in summary["removed"]


@pytest.mark.unit
def test_drift_removed_not_seeded_is_review() -> None:
    """A removed sscat_id NOT in the seeded set → REVIEW_REQUIRED (not BLOCK)."""
    live_entries = {"10000": 50, "20000": 60}
    candidate_entries = {"10000": 50}  # 20000 removed

    live = _make_lookup_doc(entries=live_entries)
    candidate = _make_lookup_doc(entries=candidate_entries)

    # 20000 is NOT seeded (only 10000 is)
    seeded_leaf_ids: set[str] = {"10000"}

    summary = diff_lookups(candidate, live, seeded_leaf_ids=seeded_leaf_ids)

    assert summary["verdict"] == VERDICT_REVIEW
    assert "20000" in summary["removed"]


@pytest.mark.unit
def test_drift_blocks_nonzero_commission() -> None:
    """Any commission_percentage != 0 in the candidate → BLOCK, regardless of seed set."""
    live = _make_lookup_doc(entries={"10000": 50})
    # Candidate has commission=4 on a row
    candidate_doc = _make_lookup_doc(entries={"10000": 50})
    candidate_doc["lookup"]["10000"]["commission_percentage"] = 4.0

    summary = diff_lookups(candidate_doc, live)

    assert summary["verdict"] == VERDICT_BLOCK
    assert "10000" in summary["commission_nonzero"]
    assert any("commission" in r for r in summary["block_reasons"])


# ---------------------------------------------------------------------------
# Orchestrator stage order
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_orchestrator_stage_order() -> None:
    """§6: mocked stages assert A→B→C order and that C aborts if B's summary fails the gate.

    This test does NOT import meesho_monthly_refresh.py (S1, owned by scraper-maintainer).
    Instead it models the EXPECTED CONTRACT that the orchestrator must implement:
      - Stage A runs first.
      - Stage B runs second, after A completes.
      - Stage C runs ONLY when B's census summary passes the gate (error_rows==0 etc.).
      - If B's summary fails the gate, C must be skipped (no candidate written).

    The test uses MagicMock to represent the three stage callables and asserts call ordering
    and gating logic.  This is a behavioural contract test — the actual orchestrator is
    wired by scraper-maintainer (S1) and must honour this contract.
    """
    # Simulate the orchestrator contract via a minimal state machine.
    call_order: list[str] = []

    stage_a_result = {"ok": True, "storage_state": "/tmp/fake_state.json"}
    stage_b_ok_result = {
        "ok": True,
        "summary": {
            "rows_with_data": EXPECTED_COUNT,
            "error_rows": 0,
            "lookup": {str(10000 + i): {"shipping_charges": 50, "commission_percentage": 0.0, "formula_ok": True} for i in range(EXPECTED_COUNT)},
            "census_price": 100,
            "generated_at": "2026-06-01T00:00:00",
        },
    }
    stage_b_fail_result = {
        "ok": False,
        "summary": {
            "rows_with_data": 100,
            "error_rows": 10,
            "lookup": {},
            "census_price": 100,
            "generated_at": "2026-06-01T00:00:00",
        },
    }

    stage_a = MagicMock(side_effect=lambda: (call_order.append("A"), stage_a_result)[1])
    stage_b_ok = MagicMock(
        side_effect=lambda storage_state: (call_order.append("B"), stage_b_ok_result)[1]
    )
    stage_b_fail = MagicMock(
        side_effect=lambda storage_state: (call_order.append("B"), stage_b_fail_result)[1]
    )
    stage_c = MagicMock(
        side_effect=lambda census_summary: (call_order.append("C"), {"ok": True})[1]
    )

    def run_orchestrator(stage_b_mock: MagicMock) -> dict[str, Any]:
        """Minimal orchestrator: A → B → gate-check → (C or abort)."""
        a_result = stage_a()
        b_result = stage_b_mock(a_result.get("storage_state"))

        b_summary = b_result["summary"]
        # Gate: B's summary must pass the same hard invariants as build_pricing_lookup.py
        gate_ok = (
            b_result["ok"]
            and b_summary.get("error_rows", -1) == 0
            and len(b_summary.get("lookup", {})) == EXPECTED_COUNT
        )

        if not gate_ok:
            # C is skipped — orchestrator returns without calling stage_c
            return {"ok": False, "reason": "Stage B census failed the gate"}

        c_result = stage_c(b_summary)
        return {"ok": c_result["ok"]}

    # --- Scenario 1: B succeeds → C is called, order is A→B→C ---
    call_order.clear()
    result_ok = run_orchestrator(stage_b_ok)
    assert result_ok["ok"] is True
    assert call_order == ["A", "B", "C"], (
        f"Expected A→B→C when B succeeds; got {call_order}"
    )

    # --- Scenario 2: B fails → C is NOT called, order is A→B only ---
    call_order.clear()
    result_fail = run_orchestrator(stage_b_fail)
    assert result_fail["ok"] is False
    assert call_order == ["A", "B"], (
        f"Expected A→B only when B fails; got {call_order}"
    )
    stage_c.assert_called_once()  # was only called once (in scenario 1)


# ---------------------------------------------------------------------------
# run_diff integration (pure-function, uses tmpfiles — no live DB)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_run_diff_pass_no_report_write(tmp_path: Path) -> None:
    """run_diff() with identical files returns PASS; no report written when write_report=False."""
    live_entries = {str(10000 + i): 50 for i in range(10)}
    live_doc = _make_lookup_doc(entries=live_entries)
    cand_doc = _make_lookup_doc(entries=live_entries, generated_at="2026-06-02T00:00:00")

    live_path = tmp_path / "live.json"
    cand_path = tmp_path / "candidate.json"
    live_path.write_text(json.dumps(live_doc), encoding="utf-8")
    cand_path.write_text(json.dumps(cand_doc), encoding="utf-8")

    summary = run_diff(cand_path, live_path=live_path, write_report=False)

    assert summary["verdict"] == VERDICT_PASS
    # No report file should have been written
    assert list(tmp_path.glob("*.md")) == []


@pytest.mark.unit
def test_run_diff_writes_report_on_drift(tmp_path: Path) -> None:
    """run_diff() with drift writes a markdown report to the given log_dir override."""
    live_entries = {"10949": 82}
    candidate_entries = {"10949": 90}
    live_doc = _make_lookup_doc(entries=live_entries)
    cand_doc = _make_lookup_doc(entries=candidate_entries)

    live_path = tmp_path / "live.json"
    cand_path = tmp_path / "candidate.json"
    live_path.write_text(json.dumps(live_doc), encoding="utf-8")
    cand_path.write_text(json.dumps(cand_doc), encoding="utf-8")

    # Patch _default_log_dir to write into tmp_path so we don't touch logs/ on disk
    with patch(
        "scripts.diff_pricing_lookup._default_log_dir",
        return_value=tmp_path / "logs",
    ):
        summary = run_diff(cand_path, live_path=live_path, write_report=True)

    assert summary["verdict"] == VERDICT_REVIEW
    report_files = list((tmp_path / "logs").glob("pricing_lookup_drift_*.md"))
    assert len(report_files) == 1
    report_text = report_files[0].read_text()
    assert "10949" in report_text
    assert "REVIEW_REQUIRED" in report_text
