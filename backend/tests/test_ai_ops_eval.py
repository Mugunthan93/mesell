"""Tests for :mod:`app.ai_ops.eval` — §6A.H (IA-RED-2 fix).

Covers:

* :class:`EvalReport` and :class:`FixtureResult` shape.
* 3 golden sets defined with the locked targets:
  smart_picker top-5 recall ≥ 80%, autofill 100% conformance,
  watermark ≥ 85%.
* :func:`run_eval` returns ``passed=False`` with 0/0 when fixtures
  file is missing.
* :func:`run_eval` scores a stub fixture file through the REAL
  ``call_gemini`` pipeline (adapter mocked) and computes the aggregate
  metric correctly.
* CI GATE — :func:`run_eval` scores the REAL on-disk 110 golden fixtures
  (50 smart_picker + 30 autofill + 30 watermark) and asserts each
  workload ``passed is True`` AND ``aggregate_metric >= target_metric``.
  ``₹0`` — the ``adapters.gemini`` SDK seam is mocked, no live Gemini call.
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


# ── run_eval — with stub fixtures (real pipeline, mocked adapter) ──────────
class TestRunEvalWithFixtures:
    async def test_with_3_fixtures_returns_3_results(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Build a stub smart_picker fixture file with 3 real-shaped entries.
        # IA-RED-2: _run_one_fixture now scores through the REAL call_gemini
        # pipeline (adapter mocked), so each fixture gets a true pass/fail.
        fixture_dir = tmp_path / "smart_picker"
        fixture_dir.mkdir(parents=True)
        fixture_path = fixture_dir / "fixtures.json"
        # One description engineered to surface the same leaf in the picker's
        # trigram top-5 (so it PASSES) and one nonsense description that won't
        # (so it FAILS) — proving the scorer discriminates, not a blanket pass.
        with fixture_path.open("w") as fh:
            json.dump(
                [
                    {
                        "id": "f1",
                        "description": "Women ethnic cotton printed straight kurti",
                        "expected_category_path": (
                            "Women Fashion > Ethnic Wear > "
                            "Kurtis, Sets & Fabrics > Kurtis"
                        ),
                        "min_acceptable_paths": [
                            "Women Fashion > Ethnic Wear > "
                            "Kurtis, Sets & Fabrics > Kurtis"
                        ],
                    },
                    {
                        "id": "f2",
                        "description": "zzz qqq xxx nonsense impossible leaf label",
                        "expected_category_path": "Nonexistent > Path > Nowhere",
                        "min_acceptable_paths": ["Nonexistent > Path > Nowhere"],
                    },
                ],
                fh,
            )

        def fake_path(workload: str) -> Path:
            return fixture_path

        monkeypatch.setattr(eval_mod, "_fixtures_path", fake_path)
        report = await run_eval("smart_picker")
        assert report.fixtures_run == 2
        assert len(report.per_fixture) == 2
        # The scorer is REAL now: at least one fixture passes, and the
        # nonsense fixture (no matching leaf) fails — proving discrimination.
        assert report.fixtures_passed >= 1
        per = {r.fixture_id: r for r in report.per_fixture}
        assert per["f2"].passed is False  # nonsense → no acceptable path in top-5
        # No fixture errored out (pipeline ran cleanly through the mock).
        assert all(r.error is None for r in report.per_fixture)


# ── CI GATE — real on-disk 110 golden fixtures, scored end-to-end ──────────
class TestRunEvalGoldenSetGate:
    """IA-RED-2 CI gate — the 110 golden fixtures are ACTUALLY scored.

    Each workload must clear its locked threshold via the REAL ``call_gemini``
    pipeline (prompt → Layer 1 → render → MOCKED adapter → Layer 2 → score).
    ``₹0`` — no live Gemini call (the ``adapters.gemini`` SDK seam is mocked
    inside ``_run_one_fixture`` per the module synthesiser).
    """

    @pytest.mark.parametrize(
        ("workload", "min_fixtures"),
        [
            ("smart_picker", 50),
            ("autofill", 30),
            ("watermark", 30),
        ],
    )
    async def test_golden_set_passes_threshold(
        self, workload: str, min_fixtures: int
    ) -> None:
        report = await run_eval(workload)  # type: ignore[arg-type]
        # Fixtures are on disk (not the missing-file path).
        assert report.fixtures_run >= min_fixtures, (
            f"{workload}: expected ≥{min_fixtures} on-disk fixtures, "
            f"got {report.fixtures_run}"
        )
        # The locked threshold is the SINGLE source of truth in _TARGET_METRICS.
        assert report.target_metric == pytest.approx(
            eval_mod._TARGET_METRICS[workload]  # type: ignore[index]
        )
        # The aggregate must clear the locked threshold …
        assert report.aggregate_metric >= report.target_metric, (
            f"{workload}: aggregate {report.aggregate_metric:.4f} "
            f"< target {report.target_metric:.4f} — "
            f"{report.fixtures_passed}/{report.fixtures_run} passed"
        )
        # … and run_eval's own verdict must agree.
        assert report.passed is True
        # No fixture errored (a synthesiser/pipeline crash would set error).
        errored = [r.fixture_id for r in report.per_fixture if r.error]
        assert not errored, f"{workload}: fixtures errored: {errored}"


# pytest-asyncio auto-mode handles async tests; no module-level marker.
