"""§19.E perf budget 4 — Per-call AI cost average.

Locked budget (BACKEND_ARCHITECTURE.md §19.E + ``MVP_ARCH §8.2`` + §6A.D):

* Per-call AI cost ≤ **₹0.05 average** measured against a 7-day rolling
  window over the ``audit_events`` table (events named ``ai_ops.cost``
  per §6A.D ``cost_tracker``).

Methodology:

1. SELECT every ``audit_events`` row with ``event_name='ai_ops.cost'``
   in the last 7 days. The payload's ``data->>'inr_cost'`` JSONB field
   carries the per-call cost in rupees.
2. Compute the arithmetic mean.
3. Assert mean ≤ ₹0.05 + 10% noise band per §19.E.

This test is a steady-state economy check — it does NOT exercise the
guardrail or budget-cap paths (those are §6A unit-test surfaces). It
ensures that as prompt-content evolves, the AVERAGE cost stays within
budget; outliers are caught by the §6A daily ₹500 cap.

The 7-day window is the §19.E lock; reducing it would amplify noise.
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

    Reads the ``audit_events`` rows where ``event_name='ai_ops.cost'`` and
    averages the ``data->>'inr_cost'`` field. Skips gracefully (with the
    sample-count surfaced) when the window contains fewer than 20 events
    — the average is statistically meaningless below that floor.
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

    rows = (
        await db.execute(
            select(AuditEvent.data).where(
                AuditEvent.event_name == "ai_ops.cost",
                AuditEvent.created_at >= cutoff,
            )
        )
    ).all()

    if len(rows) < 20:
        pytest.skip(
            f"ai_ops.cost audit events in last {ROLLING_WINDOW_DAYS}d: "
            f"only {len(rows)} (< 20) — average is statistically "
            "meaningless. Run once production traffic accumulates."
        )

    costs: list[float] = []
    for (data,) in rows:
        if not isinstance(data, dict):
            continue
        raw = data.get("inr_cost")
        if raw is None:
            continue
        try:
            costs.append(float(Decimal(str(raw))))
        except (ValueError, ArithmeticError):
            continue

    if not costs:
        pytest.skip(
            "ai_ops.cost rows in window carry no `inr_cost` payload — "
            "verify §6A.D cost_tracker emits the expected shape."
        )

    mean_cost = sum(costs) / len(costs)
    assert_value_within_budget(
        mean_cost,
        budget=BUDGET_AI_COST_PER_CALL_INR,
        label=f"ai_ops.cost mean over last {ROLLING_WINDOW_DAYS}d "
              f"(n={len(costs)})",
        unit=" INR",
    )
