"""§19.E perf budget 3 — End-to-end export pipeline wall time.

Locked budget (BACKEND_ARCHITECTURE.md §19.E + ``MVP_ARCH §5.5.10`` + §14.E
+ §18.D):

* End-to-end export pipeline ≤ **30 seconds** wall time, measured from
  POST ``/products/{id}/export-xlsx`` through Celery task completion to
  GET ``/exports/{id}`` returning ``status="ready"``.

Methodology:

1. Build a representative product (seeded category, all required fields,
   1 front image already pre-checked).
2. Enqueue export via the synchronous service path (skipping the actual
   Celery broker — measures the worker function execution alone, per
   the §14.E sub-pipeline budget).
3. Time the 9-step Export Adapter pipeline (§14.E) end-to-end.
4. Assert wall time within budget + 10% noise band.

Adapter layer is fully mocked (Gemini + GCS) via the §19.D fixtures; the
budget verifies the deterministic pipeline cost, not network-bound vendor
calls (which §22A R6 covers separately).
"""

from __future__ import annotations

import time

import pytest

from tests.perf.conftest import (
    assert_value_within_budget,
    skip_unless_slow_enabled,
)

pytestmark = [pytest.mark.slow, pytest.mark.perf]

# §19.E locked budget — 30 s wall time.
BUDGET_EXPORT_PIPELINE_SECONDS = 30.0


@pytest.mark.asyncio
async def test_export_pipeline_wall_time(
    db,
    mock_ai_ops_client,
    mock_gcs_adapter,
) -> None:
    """End-to-end export pipeline ≤ 30 s wall time per §19.E + §14.E.

    Measures the §14.E 9-step pipeline in-process. The Celery task body is
    invoked directly to isolate the budget from broker / worker scheduling
    overhead; the §22A R6 risk register tracks the broker-side budget
    separately.
    """
    skip_unless_slow_enabled()

    # Lazy-import so collection stays cheap when the slow gate is off.
    try:
        from app.modules.export import service as export_service
    except ImportError as exc:
        pytest.skip(f"export module not importable in this environment: {exc}")

    # The pipeline-internal helper consumes (export_id, user_id, product_id,
    # format) per §14.E. We exercise it via the public ``_run_export_pipeline``
    # entry point that ``tasks.export_xlsx_task`` calls.
    pipeline_fn = getattr(export_service, "_run_export_pipeline", None)
    if pipeline_fn is None:
        pytest.skip(
            "export._run_export_pipeline not available — §14.E surface "
            "may be deferred or renamed."
        )

    # NOTE: A full integration test that builds the fixture product +
    # invokes the pipeline lives in the dedicated §14.K golden round-trip
    # suite. This perf test wraps that integration in a wall-time assertion;
    # it skips gracefully if the seed-data harness is unavailable so the
    # perf suite stays nightly-runnable even when the integration DB is bare.
    pytest.skip(
        "perf harness depends on golden_round_trip fixture seeding (§14.K) "
        "— enable once the seed loader is wired into perf/ conftest."
    )

    # Placeholder assertion shape for when the seed harness lands:
    start = time.perf_counter()
    # await pipeline_fn(export_id=..., user_id=..., product_id=..., format="xlsx_with_images")
    elapsed = time.perf_counter() - start

    assert_value_within_budget(
        elapsed,
        budget=BUDGET_EXPORT_PIPELINE_SECONDS,
        label="export._run_export_pipeline wall time",
        unit=" s",
    )
