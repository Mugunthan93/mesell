"""test_monthly_refresh.py — real-orchestrator tests for meesho_monthly_refresh (S1).

Replaces the stand-in test_orchestrator_stage_order that previously lived in
test_diff_pricing_lookup.py and modelled an internal state machine without importing
the real orchestrator.

These tests import scripts.meesho_monthly_refresh.orchestrate() and patch the three
stage functions (run_stage_a, run_stage_b, run_stage_c) to assert:
  (a) Happy path: stages execute in A → B → C order.
  (b) Gate failure: orchestrate() returns exit 2 and Stage C is NEVER called when
      Stage B's summary fails the gate (error_rows != 0 OR rows_with_data != 3772).
  (c) No live-file overwrite: after Fix-1, the committed lookup file
      (LIVE_LOOKUP_PATH) is never written by the orchestrator on PASS or
      REVIEW_REQUIRED — only the gitignored candidate side-path is touched.

DB-SAFETY: No database imports, no live connection, no Playwright, no network.
           All fixtures are synthetic dicts / tmp_path only.

Marker: unit (§19.D).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Module under test — import the real orchestrator.
# importlib.util lazy helpers keep Playwright out of the module namespace so
# this import is clean without a live browser install.
# ---------------------------------------------------------------------------
import scripts.meesho_monthly_refresh as monthly_refresh  # type: ignore[import]
from scripts.meesho_monthly_refresh import (  # type: ignore[import]
    CANDIDATE_PATH,
    orchestrate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_ROWS = 3772

_STAGE_B_OK_SUMMARY: dict = {
    "rows_with_data": EXPECTED_ROWS,
    "error_rows": 0,
    "census_price": 100,
    "generated_at": "2026-06-01T00:00:00",
}

_STAGE_B_FAIL_SUMMARY: dict = {
    "rows_with_data": 100,
    "error_rows": 10,
    "census_price": 100,
    "generated_at": "2026-06-01T00:00:00",
}

_STAGE_C_PASS_RESULT: dict = {
    "ok": True,
    "verdict": "PASS",
    "reason": "",
    "candidate_path": CANDIDATE_PATH,
    "drift_summary": {"added": [], "removed": [], "shipping_changed": [], "unchanged_count": EXPECTED_ROWS},
}

_STAGE_C_REVIEW_RESULT: dict = {
    "ok": True,
    "verdict": "REVIEW_REQUIRED",
    "reason": "",
    "candidate_path": CANDIDATE_PATH,
    "drift_summary": {"added": [], "removed": [], "shipping_changed": [{"sscat_id": "10949", "old": 82, "new": 90, "delta": 8, "pct": 9.76}], "unchanged_count": EXPECTED_ROWS - 1},
}


def _make_stage_a_result(storage_state_exists: bool = False) -> dict:
    return {
        "ok": True,
        "reason": "",
        "storage_state_path": Path("/tmp/fake_state.json") if storage_state_exists else None,
    }


# ---------------------------------------------------------------------------
# (a) Happy path: A → B → C called in order
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_orchestrator_happy_path_stage_order() -> None:
    """(a) Happy path: real orchestrate() calls stages in A → B → C order."""
    call_order: list[str] = []

    async def fake_stage_a() -> dict:
        call_order.append("A")
        return _make_stage_a_result()

    async def fake_stage_b(storage_state_path: Path | None) -> dict:
        call_order.append("B")
        return {"ok": True, "reason": "", "summary": _STAGE_B_OK_SUMMARY}

    def fake_stage_c(census_summary: dict) -> dict:
        call_order.append("C")
        return _STAGE_C_PASS_RESULT

    with (
        patch.object(monthly_refresh, "run_stage_a", new=fake_stage_a),
        patch.object(monthly_refresh, "run_stage_b", new=fake_stage_b),
        patch.object(monthly_refresh, "run_stage_c", new=fake_stage_c),
    ):
        exit_code = asyncio.run(orchestrate())

    assert exit_code == 0, f"Expected exit 0 on happy path; got {exit_code}"
    assert call_order == ["A", "B", "C"], (
        f"Expected A→B→C call order; got {call_order}"
    )


@pytest.mark.unit
def test_orchestrator_happy_path_review_required_exit_0() -> None:
    """REVIEW_REQUIRED verdict returns exit 0 (candidate staged, human promotes)."""
    async def fake_stage_a() -> dict:
        return _make_stage_a_result()

    async def fake_stage_b(storage_state_path: Path | None) -> dict:
        return {"ok": True, "reason": "", "summary": _STAGE_B_OK_SUMMARY}

    def fake_stage_c(census_summary: dict) -> dict:
        return _STAGE_C_REVIEW_RESULT

    with (
        patch.object(monthly_refresh, "run_stage_a", new=fake_stage_a),
        patch.object(monthly_refresh, "run_stage_b", new=fake_stage_b),
        patch.object(monthly_refresh, "run_stage_c", new=fake_stage_c),
    ):
        exit_code = asyncio.run(orchestrate())

    assert exit_code == 0, f"Expected exit 0 on REVIEW_REQUIRED; got {exit_code}"


# ---------------------------------------------------------------------------
# (b) Stage B gate failure: exit 2, Stage C never invoked
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_orchestrator_stage_b_gate_failure_error_rows() -> None:
    """(b) orchestrate() returns exit 2 and Stage C is NOT called when error_rows != 0."""
    call_order: list[str] = []

    async def fake_stage_a() -> dict:
        call_order.append("A")
        return _make_stage_a_result()

    async def fake_stage_b_fail(storage_state_path: Path | None) -> dict:
        call_order.append("B")
        # ok=False signals the orchestrator's gate check already fired inside run_stage_b
        return {"ok": False, "reason": "Census error_rows=10 (expected 0)", "summary": _STAGE_B_FAIL_SUMMARY}

    stage_c_mock = MagicMock(name="run_stage_c")

    with (
        patch.object(monthly_refresh, "run_stage_a", new=fake_stage_a),
        patch.object(monthly_refresh, "run_stage_b", new=fake_stage_b_fail),
        patch.object(monthly_refresh, "run_stage_c", new=stage_c_mock),
    ):
        exit_code = asyncio.run(orchestrate())

    assert exit_code == 2, f"Expected exit 2 when Stage B fails; got {exit_code}"
    stage_c_mock.assert_not_called()
    assert call_order == ["A", "B"], f"Expected A→B only when B fails; got {call_order}"


@pytest.mark.unit
def test_orchestrator_stage_b_gate_failure_short_rows() -> None:
    """(b) orchestrate() returns exit 2 when rows_with_data != 3772."""
    call_order: list[str] = []

    async def fake_stage_a() -> dict:
        call_order.append("A")
        return _make_stage_a_result()

    async def fake_stage_b_short(storage_state_path: Path | None) -> dict:
        call_order.append("B")
        return {
            "ok": False,
            "reason": "Census rows_with_data=3771 (expected 3772)",
            "summary": {**_STAGE_B_FAIL_SUMMARY, "rows_with_data": 3771, "error_rows": 0},
        }

    stage_c_mock = MagicMock(name="run_stage_c")

    with (
        patch.object(monthly_refresh, "run_stage_a", new=fake_stage_a),
        patch.object(monthly_refresh, "run_stage_b", new=fake_stage_b_short),
        patch.object(monthly_refresh, "run_stage_c", new=stage_c_mock),
    ):
        exit_code = asyncio.run(orchestrate())

    assert exit_code == 2, f"Expected exit 2 for short rows_with_data; got {exit_code}"
    stage_c_mock.assert_not_called()
    assert call_order == ["A", "B"]


# ---------------------------------------------------------------------------
# (c) Live file is NEVER written by orchestrate() on PASS or REVIEW_REQUIRED
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_orchestrator_pass_does_not_write_live_file(tmp_path: Path) -> None:
    """(c) PASS: the committed live lookup path is NEVER written by orchestrate().

    Patches LIVE_LOOKUP_PATH to a temp location with known initial content,
    then asserts the content is identical after a successful PASS run.
    """
    # Set up a fake live file so we can detect any mutation
    fake_live = tmp_path / "meesho_pricing_lookup.json"
    original_content = '{"_meta": {"generated_at": "2026-05-01", "total": 1}, "lookup": {}}'
    fake_live.write_text(original_content, encoding="utf-8")

    async def fake_stage_a() -> dict:
        return _make_stage_a_result()

    async def fake_stage_b(storage_state_path: Path | None) -> dict:
        return {"ok": True, "reason": "", "summary": _STAGE_B_OK_SUMMARY}

    def fake_stage_c(census_summary: dict) -> dict:
        return {**_STAGE_C_PASS_RESULT, "candidate_path": CANDIDATE_PATH}

    with (
        patch.object(monthly_refresh, "run_stage_a", new=fake_stage_a),
        patch.object(monthly_refresh, "run_stage_b", new=fake_stage_b),
        patch.object(monthly_refresh, "run_stage_c", new=fake_stage_c),
        patch.object(monthly_refresh, "LIVE_LOOKUP_PATH", fake_live),
    ):
        exit_code = asyncio.run(orchestrate())

    assert exit_code == 0
    # The live file must be IDENTICAL to the original — orchestrate() must not touch it
    assert fake_live.read_text(encoding="utf-8") == original_content, (
        "orchestrate() must NOT write to LIVE_LOOKUP_PATH on a PASS result — "
        "the human promotes the candidate via the data PR."
    )


@pytest.mark.unit
def test_orchestrator_review_required_does_not_write_live_file(tmp_path: Path) -> None:
    """(c) REVIEW_REQUIRED: the committed live lookup path is NEVER written by orchestrate().

    Uses the same mtime-check pattern as the PASS test above.
    """
    fake_live = tmp_path / "meesho_pricing_lookup.json"
    original_content = '{"_meta": {"generated_at": "2026-05-01", "total": 1}, "lookup": {}}'
    fake_live.write_text(original_content, encoding="utf-8")

    async def fake_stage_a() -> dict:
        return _make_stage_a_result()

    async def fake_stage_b(storage_state_path: Path | None) -> dict:
        return {"ok": True, "reason": "", "summary": _STAGE_B_OK_SUMMARY}

    def fake_stage_c(census_summary: dict) -> dict:
        return {**_STAGE_C_REVIEW_RESULT, "candidate_path": CANDIDATE_PATH}

    with (
        patch.object(monthly_refresh, "run_stage_a", new=fake_stage_a),
        patch.object(monthly_refresh, "run_stage_b", new=fake_stage_b),
        patch.object(monthly_refresh, "run_stage_c", new=fake_stage_c),
        patch.object(monthly_refresh, "LIVE_LOOKUP_PATH", fake_live),
    ):
        exit_code = asyncio.run(orchestrate())

    assert exit_code == 0
    assert fake_live.read_text(encoding="utf-8") == original_content, (
        "orchestrate() must NOT write to LIVE_LOOKUP_PATH on REVIEW_REQUIRED — "
        "the human promotes the candidate via the data PR."
    )


@pytest.mark.unit
def test_orchestrator_block_does_not_write_live_file(tmp_path: Path) -> None:
    """Stage C BLOCK: live file stays untouched, exit code 4 (unchanged behavior)."""
    fake_live = tmp_path / "meesho_pricing_lookup.json"
    original_content = '{"_meta": {"generated_at": "2026-05-01", "total": 1}, "lookup": {}}'
    fake_live.write_text(original_content, encoding="utf-8")

    async def fake_stage_a() -> dict:
        return _make_stage_a_result()

    async def fake_stage_b(storage_state_path: Path | None) -> dict:
        return {"ok": True, "reason": "", "summary": _STAGE_B_OK_SUMMARY}

    def fake_stage_c(census_summary: dict) -> dict:
        return {
            "ok": False,
            "verdict": "BLOCK",
            "reason": "removed seeded leaf: 10949",
            "candidate_path": CANDIDATE_PATH,
            "drift_summary": {"block_reasons": ["removed seeded leaf: 10949"]},
        }

    with (
        patch.object(monthly_refresh, "run_stage_a", new=fake_stage_a),
        patch.object(monthly_refresh, "run_stage_b", new=fake_stage_b),
        patch.object(monthly_refresh, "run_stage_c", new=fake_stage_c),
        patch.object(monthly_refresh, "LIVE_LOOKUP_PATH", fake_live),
        # Suppress STATUS_DATA write to avoid touching real project files
        patch.object(monthly_refresh, "STATUS_DATA_PATH", tmp_path / "STATUS_DATA.md"),
    ):
        exit_code = asyncio.run(orchestrate())

    assert exit_code == 4
    assert fake_live.read_text(encoding="utf-8") == original_content, (
        "orchestrate() must NOT write to LIVE_LOOKUP_PATH on BLOCK."
    )
