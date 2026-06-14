"""Golden eval-set runners — §6A.H.

V1 ships the runner + the 3 golden-set declarations + a CLI entry point.
The fixture JSON files themselves live at
``tests/eval/<workload>/fixtures.json`` per ``MVP_ARCH §8.5`` and are
populated during §19 (test strategy) construction by the relevant AI
specialist:

* ``meesell-category-picker-builder`` — Smart Picker (50 descriptions).
* ``meesell-prompt-engineer``         — Autofill (30 product specs).
* ``meesell-image-precheck-builder``  — Watermark (30 images).

Until those fixtures land, :func:`run_eval` runs against an empty
fixture list and returns ``passed=False`` with
``fixtures_run=fixtures_passed=0`` — surfacing the fixture gap as the
intended CI signal rather than silent green.

Acceptance thresholds (locked per ``MVP_ARCH §8.5``)
----------------------------------------------------
* ``smart_picker`` — top-5 recall ≥ 80%.
* ``autofill``     — invalid enum rate = 0%.
* ``watermark``    — accuracy ≥ 85%.

Invocation paths (§6A.H)
------------------------
(a) :mod:`pytest` integration in §19 — collected under
    ``tests/test_ai_eval_*.py``.
(b) CLI: ``python -m app.ai_ops.eval --workload smart_picker``.
(c) V1.5 nightly Celery beat for LangFuse-stored regression tracking.

V1 ships (a) + (b); (c) lands when monitoring is wired in §20.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.ai_ops.cost_tracker import Workload

logger = logging.getLogger(__name__)


# ── Acceptance targets (locked per MVP_ARCH §8.5) ──────────────────────────
_TARGET_METRICS: dict[Workload, float] = {
    "smart_picker": 0.80,  # top-5 recall ≥ 80%
    "autofill": 1.00,       # invalid enum rate = 0% → conformance rate = 100%
    "watermark": 0.85,      # accuracy ≥ 85%
}


@dataclass(frozen=True)
class FixtureResult:
    """Per-fixture outcome.  One row per fixture in the golden set."""

    fixture_id: str
    expected: Any
    actual: Any
    passed: bool
    error: str | None = None


@dataclass(frozen=True)
class EvalReport:
    """Aggregate report returned by :func:`run_eval`.  See §6A.H.

    ``aggregate_metric`` is workload-specific:
      * ``smart_picker`` — top-5 recall (0.0–1.0).
      * ``autofill``     — conformance rate (1 − invalid-enum-rate).
      * ``watermark``    — accuracy (0.0–1.0).

    ``regression_from_last_run`` is ``None`` until V1.5 LangFuse-stored
    baselines land.
    """

    workload: str
    fixtures_run: int
    fixtures_passed: int
    aggregate_metric: float
    target_metric: float
    passed: bool
    per_fixture: list[FixtureResult] = field(default_factory=list)
    regression_from_last_run: float | None = None


def _fixtures_path(workload: Workload) -> Path:
    """Locate the golden-fixture JSON file for ``workload``.

    Per ``MVP_ARCH §8.5``: ``tests/eval/<workload>/fixtures.json``.
    """
    # tests/ is a sibling of app/ — resolve from this file's parent ×4.
    backend_root = Path(__file__).resolve().parents[2]
    return backend_root / "tests" / "eval" / workload / "fixtures.json"


def _load_fixtures(workload: Workload) -> list[dict[str, Any]]:
    """Load the golden fixtures from disk.

    Returns ``[]`` when the file is missing — :func:`run_eval` surfaces
    this as an EvalReport with ``passed=False`` so CI fails loudly.
    """
    path = _fixtures_path(workload)
    if not path.exists():
        logger.warning(
            "ai_ops.eval: golden fixtures missing for %s at %s — "
            "will report 0/0 (CI fail). Populated during §19.",
            workload,
            path,
        )
        return []
    with path.open() as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError(
            f"Golden fixtures at {path} must be a JSON list, got "
            f"{type(data).__name__}"
        )
    return data


async def run_eval(workload: Workload) -> EvalReport:
    """Run the golden eval set for ``workload``.

    Per §6A.H.  V1 returns ``passed=False`` until the fixture files
    land in §19 — see module docstring.

    Args:
        workload: One of the 3 V1 workloads.

    Returns:
        :class:`EvalReport` with aggregate metric and per-fixture detail.
    """
    fixtures = _load_fixtures(workload)
    target = _TARGET_METRICS[workload]

    if not fixtures:
        return EvalReport(
            workload=workload,
            fixtures_run=0,
            fixtures_passed=0,
            aggregate_metric=0.0,
            target_metric=target,
            passed=False,
            per_fixture=[],
            regression_from_last_run=None,
        )

    per_fixture: list[FixtureResult] = []
    passed_count = 0
    for fix in fixtures:
        result = await _run_one_fixture(workload, fix)
        per_fixture.append(result)
        if result.passed:
            passed_count += 1

    aggregate = passed_count / len(fixtures) if fixtures else 0.0
    return EvalReport(
        workload=workload,
        fixtures_run=len(fixtures),
        fixtures_passed=passed_count,
        aggregate_metric=aggregate,
        target_metric=target,
        passed=aggregate >= target,
        per_fixture=per_fixture,
        regression_from_last_run=None,
    )


async def _run_one_fixture(
    workload: Workload, fixture: dict[str, Any]
) -> FixtureResult:
    """Execute a single golden fixture through :func:`ai_ops.client.call_gemini`.

    V1 skeleton: full per-fixture dispatch is wired during §19 once the
    fixture schemas land (each workload's fixture has a workload-specific
    shape — Smart Picker provides ``{description, expected_top5}``,
    Autofill provides ``{spec, expected_fields, allowed_enums}``,
    Watermark provides ``{image_path, expected_has_watermark}``).  The
    body here returns a placeholder ``passed=False`` for any non-empty
    fixture so the runner skeleton is observable end-to-end without
    consuming Gemini tokens at construction time.
    """
    fixture_id = str(fixture.get("id", "unknown"))
    return FixtureResult(
        fixture_id=fixture_id,
        expected=fixture.get("expected"),
        actual=None,
        passed=False,
        error="run_eval per-fixture dispatch wired in §19 — see module docstring",
    )


def _main() -> None:  # pragma: no cover — CLI entry point
    """CLI invocation: ``python -m app.ai_ops.eval --workload smart_picker``."""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="ai_ops golden eval runner")
    parser.add_argument(
        "--workload",
        required=True,
        choices=["smart_picker", "autofill", "watermark"],
    )
    args = parser.parse_args()
    report = asyncio.run(run_eval(args.workload))
    print(
        f"{report.workload}: "
        f"{report.fixtures_passed}/{report.fixtures_run} "
        f"metric={report.aggregate_metric:.4f} "
        f"target={report.target_metric:.4f} "
        f"passed={report.passed}"
    )


if __name__ == "__main__":  # pragma: no cover
    _main()


__all__ = [
    "EvalReport",
    "FixtureResult",
    "run_eval",
]
