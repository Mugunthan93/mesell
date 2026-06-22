"""AI-BE-15/16 — Eval scoring harness runner-logic tests (IA-RED-2 guard).

Wave: qa-image-ai (Wave A).

IA-RED-2 status
---------------
``app.ai_ops.eval._run_one_fixture`` was originally a STUB.  PR #434
(``meesell-prompt-engineer``) wired the real scorer, so the stub-state
guards (``TestStubStateGuards``) that asserted ``fixtures_passed == 0``
are now self-contradicting and have been DROPPED (gate-reject fix).

What remains — ``TestRunnerAggregationLogic`` — patches ``_run_one_fixture``
with a mock scorer and asserts the RUNNER aggregation logic (how ``run_eval``
aggregates per-fixture results into an ``EvalReport``).  These tests are
scorer-independent: they will stay green regardless of what the real scorer
returns, because the mock controls the per-fixture outcome.

No real Gemini calls.  All scoring is against synthetic fixtures written
in-test via ``tmp_path``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ai_ops import eval as eval_mod
from app.ai_ops.eval import EvalReport, FixtureResult, run_eval

pytestmark = pytest.mark.unit


# ===========================================================================
# Mocked-scorer tests (runner logic validation)
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
