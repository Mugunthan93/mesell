"""§19.E perf budget 4 — Per-call AI cost average.  IA-RED-1 FIX.

Wave: qa-image-ai · fix: IA-RED-1 — column-drift repair.

Root cause of IA-RED-1
----------------------
The original test queried ``AuditEvent.event_name``, ``AuditEvent.data``,
``AuditEvent.created_at`` and filtered on ``event_name='ai_ops.cost'``.
Those columns do NOT exist on the ORM model.  The real model has:

* ``event_type  (VARCHAR 40)`` — ``cost_tracker._write_audit_row`` writes
  ``"ai.call"`` (NOT ``"ai_ops.cost"``).
* ``metadata_jsonb (JSONB)``   — carries ``{"workload": …, "cost_inr": …, …}``.
* ``occurred_at (TIMESTAMPTZ)`` — the timestamp column.

This file is the corrected version that reads the CANONICAL columns so
the ₹0.05/call ceiling is genuinely asserted against real producer data.
The companion unit test in ``test_cost_tracker_canonical_shape.py`` asserts
the producer writes exactly these field names on every call.

Methodology
-----------
1. SELECT every ``audit_events`` row with ``event_type='ai.call'`` in the
   last 7 days.  The payload's ``metadata_jsonb->>'cost_inr'`` JSONB field
   carries the per-call cost in rupees.
2. Compute the arithmetic mean.
3. Assert mean ≤ ₹0.05 + 10% noise band per §19.E.

This test is a steady-state economy check.  In CI without live AI traffic,
the test SKIPS gracefully (< 20 events).  The guard that matters is the
NEW unit-level test ``test_cost_tracker_canonical_shape.py`` which asserts
the producer writes the right columns on EVERY call.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from tests.perf.conftest import (
    assert_value_within_budget,
    skip_unless_slow_enabled,
)

pytestmark = [pytest.mark.slow, pytest.mark.perf]

# §19.E locked budget — ₹0.05 per call average.
BUDGET_AI_COST_PER_CALL_INR = 0.05

# §19.E locked window — last 7 days of audit_events.
ROLLING_WINDOW_DAYS = 7


@pytest.mark.asyncio
async def test_ai_cost_per_call_average(db) -> None:
    """7-day rolling mean AI cost per call ≤ ₹0.05 per §19.E + §6A.D.

    IA-RED-1 FIX: reads the CANONICAL audit shape written by
    ``cost_tracker._write_audit_row``:
      - ``event_type = 'ai.call'``            (NOT 'ai_ops.cost')
      - ``metadata_jsonb->>'cost_inr'``        (NOT data->>'inr_cost')
      - ``occurred_at``                        (NOT created_at)

    Skips gracefully (with sample count surfaced) when the window contains
    fewer than 20 events — statistically meaningless below that floor.
    """
    skip_unless_slow_enabled()

    from sqlalchemy import select

    try:
        from app.shared.models.audit_event import AuditEvent
    except ImportError as exc:
        pytest.skip(f"audit_event ORM model not importable: {exc}")

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=ROLLING_WINDOW_DAYS
    )

    # IA-RED-1 FIX: use the canonical ORM columns.
    # event_type = "ai.call"    (cost_tracker._write_audit_row sets this)
    # occurred_at               (the timestamp column on AuditEvent)
    # metadata_jsonb            (carries cost_inr)
    rows = (
        await db.execute(
            select(AuditEvent.metadata_jsonb).where(
                AuditEvent.event_type == "ai.call",
                AuditEvent.occurred_at >= cutoff,
            )
        )
    ).all()

    if len(rows) < 20:
        pytest.skip(
            f"ai.call audit events in last {ROLLING_WINDOW_DAYS}d: "
            f"only {len(rows)} (< 20) — average is statistically "
            "meaningless.  Run once production traffic accumulates."
        )

    costs: list[float] = []
    for (metadata_jsonb,) in rows:
        if not isinstance(metadata_jsonb, dict):
            continue
        # IA-RED-1 FIX: read 'cost_inr' (NOT 'inr_cost').
        raw = metadata_jsonb.get("cost_inr")
        if raw is None:
            continue
        try:
            costs.append(float(Decimal(str(raw))))
        except (ValueError, ArithmeticError):
            continue

    if not costs:
        pytest.skip(
            "ai.call rows in window carry no `cost_inr` in metadata_jsonb — "
            "verify §6A.D cost_tracker emits the expected shape."
        )

    mean_cost = sum(costs) / len(costs)
    assert_value_within_budget(
        mean_cost,
        budget=BUDGET_AI_COST_PER_CALL_INR,
        label=f"ai.call mean over last {ROLLING_WINDOW_DAYS}d "
              f"(n={len(costs)})",
        unit=" INR",
    )
