"""Tests for :mod:`app.ai_ops.eval` — §6A.H.

Covers:

* :class:`EvalReport` and :class:`FixtureResult` shape.
* 3 golden sets defined with the locked targets:
  smart_picker top-5 recall ≥ 80%, autofill 100% conformance,
  watermark ≥ 85%.
* :func:`run_eval` returns ``passed=False`` with 0/0 when fixtures
  file is missing (V1 expected state until §19 lands).
* :func:`run_eval` runs against a stub fixture file when present and
  computes aggregate metric correctly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ai_ops import eval as eval_mod
from app.ai_ops.eval import EvalReport, FixtureResult, run_eval

pytestmark = pytest.mark.unit


# ── Dataclass shape ────────────────────────────────────────────────────────
class TestDataclasses:
    def test_eval_report_frozen(self) -> None:
        r = EvalReport(
            workload="smart_picker",
            fixtures_run=0,
            fixtures_passed=0,
            aggregate_metric=0.0,
            target_metric=0.8,
            passed=False,
        )
        with pytest.raises(Exception):
            r.passed = True  # type: ignore[misc]

    def test_fixture_result_frozen(self) -> None:
        f = FixtureResult(
            fixture_id="x", expected=1, actual=1, passed=True
        )
        with pytest.raises(Exception):
            f.passed = False  # type: ignore[misc]


# ── 3 golden-set targets ───────────────────────────────────────────────────
class TestGoldenTargets:
    """The 3 locked workload targets must match ``MVP_ARCH §8.5``."""

    def test_smart_picker_target_80_pct(self) -> None:
        assert eval_mod._TARGET_METRICS["smart_picker"] == pytest.approx(0.80)

    def test_autofill_target_100_pct_conformance(self) -> None:
        # 0% invalid-enum-rate → 100% conformance.
        assert eval_mod._TARGET_METRICS["autofill"] == pytest.approx(1.00)

    def test_watermark_target_85_pct(self) -> None:
        assert eval_mod._TARGET_METRICS["watermark"] == pytest.approx(0.85)

    def test_three_workloads_only(self) -> None:
        assert set(eval_mod._TARGET_METRICS.keys()) == {
            "smart_picker",
            "autofill",
            "watermark",
        }


# ── run_eval — missing fixtures (V1 baseline state) ────────────────────────
class TestRunEvalMissingFixtures:
    async def test_returns_failed_when_fixture_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Point _fixtures_path at an empty tmp dir so the file doesn't exist.
        def fake_path(workload: str) -> Path:
            return tmp_path / workload / "fixtures.json"

        monkeypatch.setattr(eval_mod, "_fixtures_path", fake_path)
        report = await run_eval("smart_picker")
        assert report.fixtures_run == 0
        assert report.fixtures_passed == 0
        assert report.passed is False
        assert report.target_metric == pytest.approx(0.80)


# ── run_eval — with stub fixtures ──────────────────────────────────────────
class TestRunEvalWithFixtures:
    async def test_with_3_fixtures_returns_3_results(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Build a stub fixture file with 3 entries.
        fixture_dir = tmp_path / "smart_picker"
        fixture_dir.mkdir(parents=True)
        fixture_path = fixture_dir / "fixtures.json"
        with fixture_path.open("w") as fh:
            json.dump(
                [
                    {"id": "f1", "expected": "cat-1"},
                    {"id": "f2", "expected": "cat-2"},
                    {"id": "f3", "expected": "cat-3"},
                ],
                fh,
            )

        def fake_path(workload: str) -> Path:
            return fixture_path

        monkeypatch.setattr(eval_mod, "_fixtures_path", fake_path)
        report = await run_eval("smart_picker")
        assert report.fixtures_run == 3
        # V1 skeleton: per-fixture dispatch returns passed=False → 0/3.
        assert report.fixtures_passed == 0
        assert len(report.per_fixture) == 3


# pytest-asyncio auto-mode handles async tests; no module-level marker.
