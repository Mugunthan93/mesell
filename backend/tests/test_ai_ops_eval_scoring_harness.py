"""AI-BE-15/16 — Eval scoring harness guard tests (IA-RED-2 guard).

Wave: qa-image-ai (Wave A).

IA-RED-2 status
---------------
``app.ai_ops.eval._run_one_fixture`` is a STUB returning ``passed=False``
for every fixture unconditionally (see eval.py L186-193 docstring note:
"body here returns a placeholder passed=False").  This means ``run_eval``
can NEVER report a real metric — the 30 watermark + 30 autofill golden
fixtures EXIST on disk but are never scored.

Per the plan §2 Wave A contract:
  - IA-RED-2 is APP CODE owned by the AI lead
    (``meesell-ai-coordinator`` / ``meesell-prompt-engineer``).
  - The QA writer's obligation is: write the MOCKED scoring harness tests
    that will be green ONCE the AI lead wires ``_run_one_fixture``.
  - Until then these tests assert the STUB behaviour (0/0 fail-loud) so
    CI does NOT silently green-pass with 0 coverage.

This file therefore does TWO things:
1. **Stub-state guards** — assert the current ``run_eval`` behavior is the
   documented stub (0/N passed=False) so any silent regression from the stub
   is caught.
2. **Mocked-scorer tests** — patch ``_run_one_fixture`` to return a real
   scoring function and assert the aggregate metrics are computed correctly
   by ``run_eval`` — testing the RUNNER logic (which the AI lead must not
   break while wiring the scorer).

When the AI lead wires ``_run_one_fixture``, the mocked-scorer tests already
pass (runner logic correct); only the stub-state tests need to be
re-evaluated and the fixture file paths will be live.

No real Gemini calls.  All scoring is against pre-written fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ai_ops import eval as eval_mod
from app.ai_ops.eval import EvalReport, FixtureResult, run_eval

pytestmark = pytest.mark.unit


# ===========================================================================
# Part 1: Stub-state guards (document the current _run_one_fixture behavior)
# ===========================================================================

class TestStubStateGuards:
    """Assert the stub returns passed=False for all fixtures.

    These tests LOCK the current stub behavior so any accidental change to
    the stub (making it return True without real scoring) is caught.
    """

    async def test_watermark_with_real_fixtures_all_return_false_per_stub(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With real watermark fixtures, stub returns 0/30 passed=False."""
        # Point _fixtures_path at the real watermark fixtures
        backend_root = Path(__file__).resolve().parents[1]
        wm_path = backend_root / "tests" / "eval" / "watermark" / "fixtures.json"
        if not wm_path.exists():
            pytest.skip(f"Watermark fixtures not found at {wm_path}")

        monkeypatch.setattr(
            eval_mod,
            "_fixtures_path",
            lambda workload: wm_path if workload == "watermark" else wm_path,
        )

        report = await run_eval("watermark")
        # Stub: all fixtures return passed=False
        assert report.fixtures_passed == 0
        assert report.fixtures_run == 30
        # Stub state: NOT passing (no real scoring)
        assert report.passed is False

    async def test_autofill_with_real_fixtures_all_return_false_per_stub(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With real autofill fixtures, stub returns 0/30 passed=False."""
        backend_root = Path(__file__).resolve().parents[1]
        af_path = backend_root / "tests" / "eval" / "autofill" / "fixtures.json"
        if not af_path.exists():
            pytest.skip(f"Autofill fixtures not found at {af_path}")

        monkeypatch.setattr(
            eval_mod,
            "_fixtures_path",
            lambda workload: af_path if workload == "autofill" else af_path,
        )

        report = await run_eval("autofill")
        assert report.fixtures_passed == 0
        assert report.fixtures_run == 30
        assert report.passed is False


# ===========================================================================
# Part 2: Mocked-scorer tests (runner logic validation)
#
# These tests REPLACE _run_one_fixture with a scoring function that mirrors
# what the AI lead must implement.  They assert the RUNNER aggregation logic
# is correct.  When the real _run_one_fixture is wired, these become
# regression guards for the runner (not the scorer).
# ===========================================================================

class TestRunnerAggregationLogic:
    """Verify run_eval's aggregation logic when _run_one_fixture returns real results."""

    async def test_watermark_accuracy_above_85_pct_passes(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Watermark: 26/30 correct = 86.7% >= 85% target → passed=True.

        This is the AI-BE-15 guard: once the AI lead wires the scorer,
        the runner must compute ≥85% and report passed=True.
        """
        # 26 correct watermark predictions out of 30
        fixture_dir = tmp_path / "watermark"
        fixture_dir.mkdir()
        fixtures = [
            {"id": f"wm_{i:03d}", "expected_has_watermark": (i % 2 == 0)}
            for i in range(1, 31)
        ]
        (fixture_dir / "fixtures.json").write_text(json.dumps(fixtures))

        monkeypatch.setattr(
            eval_mod, "_fixtures_path", lambda w: fixture_dir / "fixtures.json"
        )

        # Mock _run_one_fixture: 26 pass, 4 fail
        pass_ids = {f"wm_{i:03d}" for i in range(1, 27)}  # first 26 pass

        async def _mock_run_one_fixture(workload, fixture):
            fid = str(fixture.get("id", ""))
            passed = fid in pass_ids
            return FixtureResult(
                fixture_id=fid,
                expected=fixture.get("expected_has_watermark"),
                actual=fixture.get("expected_has_watermark") if passed else None,
                passed=passed,
            )

        monkeypatch.setattr(eval_mod, "_run_one_fixture", _mock_run_one_fixture)

        report = await run_eval("watermark")

        assert report.fixtures_run == 30
        assert report.fixtures_passed == 26
        assert report.aggregate_metric == pytest.approx(26 / 30)
        # 86.7% >= 85% target → passed
        assert report.passed is True

    async def test_watermark_accuracy_below_85_pct_fails(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Watermark: 24/30 correct = 80% < 85% target → passed=False."""
        fixture_dir = tmp_path / "watermark"
        fixture_dir.mkdir()
        fixtures = [{"id": f"wm_{i:03d}", "expected_has_watermark": True} for i in range(30)]
        (fixture_dir / "fixtures.json").write_text(json.dumps(fixtures))

        monkeypatch.setattr(
            eval_mod, "_fixtures_path", lambda w: fixture_dir / "fixtures.json"
        )

        pass_ids = {f"wm_{i:03d}" for i in range(24)}

        async def _mock_run_one(workload, fixture):
            fid = str(fixture.get("id", ""))
            return FixtureResult(
                fixture_id=fid, expected=True,
                actual=True if fid in pass_ids else None,
                passed=fid in pass_ids,
            )

        monkeypatch.setattr(eval_mod, "_run_one_fixture", _mock_run_one)

        report = await run_eval("watermark")

        assert report.fixtures_passed == 24
        assert report.passed is False
        assert report.aggregate_metric < 0.85

    async def test_autofill_100_pct_enum_conformance_passes(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Autofill: 30/30 enum-conformant = 100% → passed=True.

        This is the AI-BE-16 guard.
        """
        fixture_dir = tmp_path / "autofill"
        fixture_dir.mkdir()
        fixtures = [
            {
                "id": f"af_{i:03d}",
                "expected_fields": {"fabric": "Cotton"},
                "allowed_enums": {"fabric": ["Cotton", "Silk"]},
            }
            for i in range(30)
        ]
        (fixture_dir / "fixtures.json").write_text(json.dumps(fixtures))

        monkeypatch.setattr(
            eval_mod, "_fixtures_path", lambda w: fixture_dir / "fixtures.json"
        )

        # All 30 pass (100% conformance)
        async def _mock_run_one(workload, fixture):
            fid = str(fixture.get("id", ""))
            return FixtureResult(
                fixture_id=fid,
                expected=fixture.get("expected_fields"),
                actual={"fabric": "Cotton"},
                passed=True,
            )

        monkeypatch.setattr(eval_mod, "_run_one_fixture", _mock_run_one)

        report = await run_eval("autofill")

        assert report.fixtures_run == 30
        assert report.fixtures_passed == 30
        assert report.aggregate_metric == pytest.approx(1.0)
        assert report.passed is True

    async def test_autofill_any_invalid_enum_fails(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Autofill: even 1 invalid enum out of 30 → conformance < 100% → passed=False."""
        fixture_dir = tmp_path / "autofill"
        fixture_dir.mkdir()
        fixtures = [{"id": f"af_{i:03d}"} for i in range(30)]
        (fixture_dir / "fixtures.json").write_text(json.dumps(fixtures))

        monkeypatch.setattr(
            eval_mod, "_fixtures_path", lambda w: fixture_dir / "fixtures.json"
        )

        # 29 pass, 1 fails (1 invalid enum)
        async def _mock_run_one(workload, fixture):
            fid = str(fixture.get("id", ""))
            passed = fid != "af_029"
            return FixtureResult(
                fixture_id=fid, expected={}, actual={}, passed=passed
            )

        monkeypatch.setattr(eval_mod, "_run_one_fixture", _mock_run_one)

        report = await run_eval("autofill")

        assert report.fixtures_passed == 29
        assert report.passed is False  # < 100% conformance

    async def test_per_fixture_results_length_matches_fixtures_run(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """run_eval returns one FixtureResult per fixture (runner completeness)."""
        fixture_dir = tmp_path / "watermark"
        fixture_dir.mkdir()
        fixtures = [{"id": f"wm_{i}"} for i in range(5)]
        (fixture_dir / "fixtures.json").write_text(json.dumps(fixtures))

        monkeypatch.setattr(
            eval_mod, "_fixtures_path", lambda w: fixture_dir / "fixtures.json"
        )

        async def _mock_run_one(workload, fixture):
            return FixtureResult(
                fixture_id=str(fixture["id"]), expected=None, actual=None, passed=True
            )

        monkeypatch.setattr(eval_mod, "_run_one_fixture", _mock_run_one)

        report = await run_eval("watermark")

        assert len(report.per_fixture) == 5
        assert report.fixtures_run == 5
