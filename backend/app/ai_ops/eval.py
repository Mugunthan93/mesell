"""Golden eval-set scorer — §6A.H (IA-RED-2 fix).

V1 ships the scorer + the 3 golden-set declarations + a CLI entry point.
The fixture JSON files live at ``tests/eval/<workload>/fixtures.json`` per
``MVP_ARCH §8.5`` and were populated during §22 acceptance remediation by
the relevant AI specialist:

* ``meesell-category-picker-builder`` — Smart Picker (50 descriptions).
* ``meesell-prompt-engineer``         — Autofill (30 product specs).
* ``meesell-image-precheck-builder``  — Watermark (30 images).

:func:`run_eval` scores every on-disk fixture by flowing it through the
REAL :func:`ai_ops.client.call_gemini` 9-step pipeline (prompt resolve →
Layer 1 prefix → render → adapter → Layer 2 parse/validate → return),
with the ``adapters.gemini`` SDK seam mocked so NO live Gemini call fires
(``₹0`` in CI, no API key consumed).  The mocked adapter returns a
**derived canonical response synthesised per fixture** from the SAME
deterministic decision signal the three standalone runners encode
(``tests/eval/smart_picker/run_eval.py`` trigram overlap,
``tests/eval/autofill/run_autofill_eval.py`` enum-conformance,
``tests/eval/watermark/run_watermark_eval.py`` ``detect_watermark`` rules).
The infra-bound non-SDK seams (budget reservation, cost record, LangFuse
trace) are neutralised locally so the scorer stays a pure, no-I/O ``unit``
check.

SCOPE BOUNDARY — this scorer proves the **pipeline + Layer-2 guardrail +
scoring** are correct with a mocked adapter; it does NOT prove live-model
accuracy.  Live-model accuracy + per-call cost land in the V1.5 staging-key
runner once ``GEMINI_API_KEY`` is available (see §20 / STATUS_AI Next).

When a fixture file is missing, :func:`run_eval` runs against an empty
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
(a) :mod:`pytest` integration — collected under
    ``tests/test_ai_ops_eval.py`` (rides gate-1).
(b) CLI: ``python -m app.ai_ops.eval --workload smart_picker``.
(c) V1.5 nightly Celery beat for LangFuse-stored regression tracking.

V1 ships (a) + (b); (c) lands when monitoring is wired in §20.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

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


# ── Per-workload prompt ids (V1 hardcoded — §6A.G) ─────────────────────────
_PROMPT_ID: dict[Workload, str] = {
    "smart_picker": "smart_picker.v1",
    "autofill": "autofill.v1",
    "watermark": "watermark.v1",
}

# A non-zero placeholder image for the watermark vision path.  The adapter
# is mocked, so the bytes are never decoded — they only satisfy
# ``call_gemini``'s ``_validate_workload_args`` (watermark requires
# ``image_bytes is not None``).
_PLACEHOLDER_IMAGE_BYTES = b"\xff\xd8\xff\xe0eval-fixture-placeholder"

# Smart-picker synthesis ranks the full Meesho leaf tree by the picker's
# own trigram-overlap signal — the SAME ranking
# ``tests/eval/smart_picker/run_eval.py`` uses.  Cached after first load.
_SMART_PICKER_TOP_K = 5


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


# Lazily loaded, module-cached: picker module + leaf list for smart_picker
# synthesis.  Loaded in isolation (importlib from file) to mirror the
# standalone runner and avoid pulling the category package env gate.
_picker_cache: Any | None = None
_leaves_cache: list[dict[str, str]] | None = None


def _load_picker() -> Any:
    """Load ``modules/category/picker.py`` in isolation (mirrors run_eval.py)."""
    global _picker_cache
    if _picker_cache is None:
        picker_path = (
            _backend_root() / "app" / "modules" / "category" / "picker.py"
        )
        spec = importlib.util.spec_from_file_location("picker_iso_eval", picker_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _picker_cache = module
    return _picker_cache


def _load_leaves() -> list[dict[str, str]]:
    """Load the 3,772-leaf tree as ``[{leaf_name, path}]`` (mirrors run_eval.py)."""
    global _leaves_cache
    if _leaves_cache is None:
        tree_path = (
            _backend_root() / "app" / "data" / "meesho_category_tree.json"
        )
        tree = json.loads(tree_path.read_text())
        _leaves_cache = [
            {"leaf_name": c["leaf_name"], "path": " > ".join(c["path"])}
            for c in tree["categories"]
        ]
    return _leaves_cache


def _smart_picker_top5_paths(description: str) -> list[str]:
    """Top-5 leaf paths by the picker's trigram-overlap signal.

    Mirrors ``tests/eval/smart_picker/run_eval.py::_top5_paths`` exactly —
    same ranking, same tie-break — so the synthesised response tracks the
    standalone runner's decision signal (do NOT diverge).
    """
    picker = _load_picker()
    leaves = _load_leaves()
    q_trigrams = picker._trigrams(description)
    scored: list[tuple[float, str, str]] = []
    for leaf in leaves:
        leaf_text = f"{leaf['leaf_name']} {leaf['path']}"
        overlap = picker._overlap(picker._trigrams(leaf_text), q_trigrams)
        scored.append((overlap, leaf["leaf_name"], leaf["path"]))
    # overlap DESC, leaf_name ASC, path ASC — total + deterministic.
    scored.sort(key=lambda t: (-t[0], t[1], t[2]))
    return [path for _, _, path in scored[:_SMART_PICKER_TOP_K]]


def _watermark_detect(signals: dict[str, Any]) -> bool:
    """Mirror ``tests/eval/watermark/run_watermark_eval.py::detect_watermark``.

    Re-implemented from the SAME rule set (do NOT diverge); the standalone
    runner is not importable as a package (``tests/`` is not on the app
    path), so the rules are mirrored here verbatim.
    """
    has_overlay_text = signals.get("has_overlay_text", False)
    is_product_own_label = signals.get("is_product_own_label", False)
    has_corner_signature = signals.get("has_corner_signature", False)
    has_url_or_phone = signals.get("has_url_or_phone", False)
    has_logo_overlay = signals.get("has_logo_overlay", False)

    overlay_present = (
        has_overlay_text
        or has_logo_overlay
        or has_corner_signature
        or has_url_or_phone
    )
    if is_product_own_label and not overlay_present:
        return False
    if has_overlay_text:
        return True
    if has_url_or_phone:
        return True
    if has_corner_signature:
        return True
    if has_logo_overlay:
        return True
    return False


def _synthesise_response(workload: Workload, fixture: dict[str, Any]) -> str:
    """Build the canonical Gemini response JSON the mocked adapter returns.

    The synthesised JSON is derived from the same deterministic decision
    signal each standalone runner encodes, AND conforms to the Layer-2
    guardrail shape for the workload so the REAL pipeline accepts it.  A
    synthesiser that emits guardrail-invalid JSON is a synthesiser bug to
    fix here — never a reason to tune a prompt or edit a fixture.
    """
    if workload == "smart_picker":
        top5 = _smart_picker_top5_paths(fixture["description"])
        # Guardrail shape: {"suggestions": [{category_id, confidence, reasons}]}.
        # Confidence descends within [0,1]; category_id carries the leaf path
        # so the scorer can compare against min_acceptable_paths.
        suggestions = [
            {
                "category_id": path,
                "confidence": round(0.95 - 0.05 * i, 2),
                "reasons": ["trigram-overlap rank"],
            }
            for i, path in enumerate(top5)
        ]
        return json.dumps({"suggestions": suggestions})

    if workload == "autofill":
        # Guardrail shape: {"fields": {canonical: value}}.  The runner's
        # signal is "every expected_fields value is an exact allowlist member"
        # — emit expected_fields verbatim; the REAL Layer-2 enum check bites.
        return json.dumps({"fields": dict(fixture["expected_fields"])})

    # watermark — guardrail shape: {"has_watermark": bool, "confidence": float}.
    has_wm = _watermark_detect(fixture.get("signals", {}))
    return json.dumps({"has_watermark": has_wm, "confidence": 0.9})


def _build_call_args(
    workload: Workload, fixture: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reconstruct ``call_gemini`` prompt_vars + kwargs from a fixture.

    The adapter is mocked, so prompt content does not affect scoring — the
    vars only need to render without error and the watermark path needs
    ``image_bytes``; autofill needs ``allowed_enums`` so Layer 2 enforces.
    """
    if workload == "smart_picker":
        prompt_vars = {
            "description": fixture["description"],
            "compressed_tree": "{}",  # adapter mocked — content immaterial
        }
        return prompt_vars, {}

    if workload == "autofill":
        prompt_vars = {
            "product_spec": fixture["product_description"],
            "schema": "",  # adapter mocked — content immaterial
        }
        return prompt_vars, {"allowed_enums": fixture["allowed_enums"]}

    # watermark — vision path: empty vars, image_bytes required.
    return {}, {"image_bytes": _PLACEHOLDER_IMAGE_BYTES}


def _score(
    workload: Workload, fixture: dict[str, Any], parsed: Any
) -> tuple[bool, Any]:
    """Score ``AIResponse.parsed`` against the fixture's expected output.

    Returns ``(passed, actual)``.  ``actual`` captures the salient slice of
    ``parsed`` for the FixtureResult.

    * ``smart_picker`` — PASS iff any ``min_acceptable_paths`` entry is in
      the parsed top-5 ``category_id`` list.
    * ``autofill``     — PASS iff zero enum-constrained field is off its
      allowlist (Layer 2 already drops, so this is a belt-and-braces check).
    * ``watermark``    — PASS iff parsed ``has_watermark`` equals the
      fixture's ``expected_has_watermark``.
    """
    if not isinstance(parsed, dict):
        return False, parsed

    if workload == "smart_picker":
        suggestions = parsed.get("suggestions") or []
        got_ids = [
            s.get("category_id")
            for s in suggestions
            if isinstance(s, dict)
        ]
        accept = set(
            fixture.get("min_acceptable_paths")
            or [fixture["expected_category_path"]]
        )
        passed = any(cid in accept for cid in got_ids)
        return passed, got_ids

    if workload == "autofill":
        fields = parsed.get("fields") or {}
        allowed = fixture.get("allowed_enums", {})
        off_allowlist = [
            name
            for name, value in fields.items()
            if name in allowed and value not in allowed[name]
        ]
        return (len(off_allowlist) == 0), {"off_allowlist": off_allowlist}

    # watermark
    got = parsed.get("has_watermark")
    expected = bool(fixture["expected_has_watermark"])
    return (got == expected), got


@contextlib.contextmanager
def _mocked_pipeline_seams(workload: Workload, fixture: dict[str, Any]):
    """Mock the SDK adapter + neutralise the infra-bound non-SDK seams.

    The adapter (``generate_text`` / ``generate_vision``) returns the
    per-fixture synthesised canonical response — NO live Gemini call.  The
    budget reservation, cost record, and LangFuse trace seams are stubbed so
    the scorer is a pure no-I/O ``unit`` check (no Valkey / Postgres / network).
    The REAL prompt-resolve, Layer-1 prefix, render, and Layer-2 parse/
    validate steps run untouched.
    """
    from app.adapters.gemini import GeminiResponse

    response_text = _synthesise_response(workload, fixture)
    gemini_response = GeminiResponse(
        text=response_text,
        input_tokens=0,
        output_tokens=0,
        finish_reason="STOP",
        raw={"synthesised": True},
    )
    adapter_mock = AsyncMock(return_value=gemini_response)

    with (
        patch("app.adapters.gemini.generate_text", adapter_mock),
        patch("app.adapters.gemini.generate_vision", adapter_mock),
        patch(
            "app.ai_ops.budget_cap.check_and_reserve",
            new=AsyncMock(return_value="eval-reservation"),
        ),
        patch(
            "app.ai_ops.budget_cap.release_reservation",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.ai_ops.cost_tracker.record",
            new=AsyncMock(return_value=0.0),
        ),
        patch(
            "app.adapters.langfuse.trace",
            new=AsyncMock(return_value=None),
        ),
    ):
        yield adapter_mock


async def _run_one_fixture(
    workload: Workload, fixture: dict[str, Any]
) -> FixtureResult:
    """Score a single golden fixture through the REAL ``call_gemini`` pipeline.

    Flow: synthesise a per-fixture canonical Gemini response from the same
    deterministic decision signal the standalone runners encode → mock the
    ``adapters.gemini`` SDK seam (and neutralise budget/cost/trace I/O) →
    call the REAL :func:`ai_ops.client.call_gemini` (prompt resolve → Layer 1
    → render → mocked adapter → Layer 2 parse/validate → return) → score
    ``AIResponse.parsed`` vs the fixture's expected output per workload.

    ``₹0``: no live Gemini call, no API key consumed.  Any guardrail-invalid
    synthesis surfaces as ``passed=False`` (a synthesiser bug to fix here),
    NOT a reason to tune a prompt or edit a fixture.
    """
    # Local import — avoids an ai_ops import cycle at module load.
    from app.ai_ops import client as ai_client

    fixture_id = str(fixture.get("id", "unknown"))
    expected = _expected_for(workload, fixture)

    try:
        prompt_vars, kwargs = _build_call_args(workload, fixture)
        ctx = ai_client.AICallContext(workload=workload, user_id=uuid4())
        with _mocked_pipeline_seams(workload, fixture):
            response = await ai_client.call_gemini(
                ctx,
                _PROMPT_ID[workload],
                prompt_vars,
                **kwargs,
            )
        passed, actual = _score(workload, fixture, response.parsed)
        return FixtureResult(
            fixture_id=fixture_id,
            expected=expected,
            actual=actual,
            passed=passed,
            error=None,
        )
    except Exception as exc:  # noqa: BLE001 — surface as a failed fixture, not a crash
        logger.warning(
            "ai_ops.eval: fixture %s (%s) raised: %r", fixture_id, workload, exc
        )
        return FixtureResult(
            fixture_id=fixture_id,
            expected=expected,
            actual=None,
            passed=False,
            error=f"{type(exc).__name__}: {exc}",
        )


def _expected_for(workload: Workload, fixture: dict[str, Any]) -> Any:
    """Salient expected slice for the FixtureResult row, per workload."""
    if workload == "smart_picker":
        return fixture.get("min_acceptable_paths") or [
            fixture.get("expected_category_path")
        ]
    if workload == "autofill":
        return fixture.get("expected_fields")
    return bool(fixture.get("expected_has_watermark"))


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
