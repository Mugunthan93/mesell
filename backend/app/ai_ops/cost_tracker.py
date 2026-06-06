"""Per-call AI cost recording — §6A.D.

Computes per-call cost in INR from gemini-2.5-flash token counts and
persists in three places:

1. ``audit_events`` table (direct ORM write).  Locked exception to the
   audit_mw post-commit pattern per §6A.D + §15.E exception list —
   :func:`record` is invoked from BOTH FastAPI sync paths AND Celery
   worker async paths; the worker has no request close to hook so the
   write happens inline here.

2. Valkey DB 0 daily-cost counter (``ai:cost:daily:{YYYY-MM-DD}``).
   This counter is the *committed* total — pending reservations live on
   a separate key (see :mod:`ai_ops.budget_cap`).  :func:`record`
   delegates the daily-committed bump + reservation release to
   :func:`ai_ops.budget_cap.release_reservation` when a ``reservation_id``
   is supplied (per the 9-step internal flow in §6A.C).

3. Valkey DB 0 per-user-per-hour counter
   (``ai:cost:user:{user_id}:hourly:{YYYY-MM-DD-HH}``).  Per
   ``MVP_ARCH §10.7`` this counter feeds the per-user usage analytics —
   distinct from the per-user feature *rate limits* in
   :mod:`core.plan_guard` which use a sorted-set sliding window.

Cost formula (per ``MVP_ARCH §8.2``)
-------------------------------------
``cost_inr = (input_tokens * RATE_INPUT_PER_1K + output_tokens *
RATE_OUTPUT_PER_1K) / 1000``.  ``RATE_*`` constants are gemini-2.5-flash
specific and lock at module level.  Environment overrides
(``AI_RATE_INPUT_PER_1K`` / ``AI_RATE_OUTPUT_PER_1K``) are honoured via
defensive ``getattr(settings, ..., MODULE_CONSTANT)`` per §6A.D footnote
("configurable via env if rates change") — this avoids adding fields to
the locked §5.D Settings table for a future-amendment concern.

Daily-counter timezone
----------------------
Day boundary keys use **Asia/Kolkata** per §6A.F (the global ₹500 cap
is region-local).  :func:`_today_kolkata_str` returns
``"YYYY-MM-DD"`` for the current Kolkata-local date.
"""

from __future__ import annotations

import logging
import zoneinfo
from datetime import datetime
from typing import Literal, cast
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.shared.config import settings
from app.shared.database import AsyncSessionLocal
from app.shared.models.audit_event import AuditEvent
from app.shared.valkey import get_valkey_otp

logger = logging.getLogger(__name__)

# ── Workload literal type re-export ────────────────────────────────────────
# The 3 AI workloads §6A recognises.  Type-identical across cost_tracker,
# budget_cap, guardrail, client — adding a workload is a 6-file edit by
# design (per §6A.B locked invariant).
Workload = Literal["smart_picker", "autofill", "watermark"]


# ── Rate constants (gemini-2.5-flash; per MVP_ARCH §8.2) ───────────────────
RATE_INPUT_PER_1K: float = 0.0078
"""INR cost per 1,000 input tokens.  Locked at module level per §6A.D."""

RATE_OUTPUT_PER_1K: float = 0.031
"""INR cost per 1,000 output tokens.  Locked at module level per §6A.D."""

# ── Timezone (per §6A.F lock) ──────────────────────────────────────────────
_KOLKATA_TZ = zoneinfo.ZoneInfo("Asia/Kolkata")
"""Day-boundary timezone for the ₹500 daily cap.  Configurable in §5.D
via ``AI_BUDGET_RESET_TZ`` for V1.5 multi-region (V1 always Asia/Kolkata).
"""

# ── Valkey keyspace ─────────────────────────────────────────────────────────
_DAILY_KEY_FMT = "ai:cost:daily:{date}"
_USER_HOURLY_KEY_FMT = "ai:cost:user:{user_id}:hourly:{date_hour}"

# Counter TTL — 25 hours so the daily key survives the midnight reset
# window without being purged mid-day by ``allkeys-lru`` eviction.
_DAILY_KEY_TTL_SECONDS = 90_000

# Per-user hourly counter TTL — 2 hours, generous tail for analytics
# read-back after the hour boundary.
_USER_HOURLY_KEY_TTL_SECONDS = 7_200


def _today_kolkata_str() -> str:
    """``YYYY-MM-DD`` for the current Kolkata-local date.  §6A.F locked."""
    return datetime.now(_KOLKATA_TZ).strftime("%Y-%m-%d")


def _hour_kolkata_str() -> str:
    """``YYYY-MM-DD-HH`` for the current Kolkata-local hour."""
    return datetime.now(_KOLKATA_TZ).strftime("%Y-%m-%d-%H")


def compute_cost_inr(input_tokens: int, output_tokens: int) -> float:
    """Pure cost formula — exposed for :mod:`ai_ops.budget_cap` pre-call estimate.

    Args:
        input_tokens: Prompt-side token count.
        output_tokens: Response-side token count.

    Returns:
        Cost in INR (float).  Negative inputs treated as zero.
    """
    in_rate = cast(float, getattr(settings, "AI_RATE_INPUT_PER_1K", RATE_INPUT_PER_1K))
    out_rate = cast(
        float, getattr(settings, "AI_RATE_OUTPUT_PER_1K", RATE_OUTPUT_PER_1K)
    )
    return (max(0, input_tokens) * in_rate + max(0, output_tokens) * out_rate) / 1000.0


async def record(
    user_id: UUID,
    workload: Workload,
    input_tokens: int,
    output_tokens: int,
    *,
    reservation_id: str | None = None,
) -> float:
    """Record a single AI call's cost.  See §6A.D.

    Persists ``audit_events`` row, releases the budget reservation
    (which itself bumps the daily-committed counter), and increments the
    per-user-per-hour analytics counter.

    Args:
        user_id: Seller UUID — FK to ``users.id`` (RESTRICT).
        workload: One of ``"smart_picker"`` / ``"autofill"`` / ``"watermark"``.
        input_tokens: Prompt-side token count from
            :class:`adapters.gemini.GeminiResponse`.
        output_tokens: Response-side token count.
        reservation_id: ID returned by
            :func:`ai_ops.budget_cap.check_and_reserve`.  When supplied
            (the §6A.C 9-step flow always supplies it) the daily counter
            adjustment is delegated to the reservation release path.
            ``None`` is permitted only for fallback/budget-skip paths
            where no reservation was ever created.

    Returns:
        The cost in INR for this call.
    """
    cost_inr = compute_cost_inr(input_tokens, output_tokens)

    # 1. Write the audit row (drop-on-failure with WARNING — cost record
    #    is informational; AI-call success path MUST NOT regress on audit
    #    write failure).
    await _write_audit_row(
        user_id=user_id,
        workload=workload,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_inr=cost_inr,
    )

    # 2. Release the reservation (this bumps the daily-committed counter
    #    with the actual cost and drops the pending reservation).
    if reservation_id is not None:
        # Local import to break the cost_tracker ↔ budget_cap module-load
        # cycle (budget_cap imports compute_cost_inr from here).
        from app.ai_ops.budget_cap import release_reservation

        await release_reservation(reservation_id, cost_inr)

    # 3. Bump per-user-per-hour analytics counter (separate from the
    #    feature rate limits in core/plan_guard).
    try:
        client = await get_valkey_otp()
        key = _USER_HOURLY_KEY_FMT.format(
            user_id=str(user_id), date_hour=_hour_kolkata_str()
        )
        await client.incrbyfloat(key, cost_inr)
        await client.expire(key, _USER_HOURLY_KEY_TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001 — analytics counter is best-effort
        logger.warning(
            "cost_tracker user-hourly bump failed (user=%s workload=%s): %r",
            user_id,
            workload,
            exc,
        )

    return cost_inr


async def get_daily_spend() -> float:
    """Return total INR spent today (Asia/Kolkata).  §6A.D public surface.

    Returns the *committed* (post-release) counter — does NOT include
    in-flight reservations.  See :func:`ai_ops.budget_cap.get_budget_status`
    for the committed+pending sum used by the 100% hard-stop check.
    """
    client = await get_valkey_otp()
    key = _DAILY_KEY_FMT.format(date=_today_kolkata_str())
    raw = await client.get(key)
    return float(raw) if raw is not None else 0.0


async def get_user_hourly_spend(user_id: UUID) -> float:
    """Return INR spent by ``user_id`` in the current Kolkata hour."""
    client = await get_valkey_otp()
    key = _USER_HOURLY_KEY_FMT.format(
        user_id=str(user_id), date_hour=_hour_kolkata_str()
    )
    raw = await client.get(key)
    return float(raw) if raw is not None else 0.0


# ── Internals ──────────────────────────────────────────────────────────────
async def _write_audit_row(
    *,
    user_id: UUID,
    workload: Workload,
    input_tokens: int,
    output_tokens: int,
    cost_inr: float,
) -> None:
    """Direct ORM write to ``audit_events``.  Drops on failure with WARNING.

    Locked exception to the audit_mw post-commit pattern per §6A.D + §15.E.
    """
    try:
        async with AsyncSessionLocal() as session:
            row = AuditEvent(
                user_id=user_id,
                event_type="ai.call",
                entity_type=None,
                entity_id=None,
                diff_jsonb=None,
                metadata_jsonb={
                    "workload": workload,
                    "input_tokens": int(input_tokens),
                    "output_tokens": int(output_tokens),
                    "cost_inr": float(cost_inr),
                },
            )
            session.add(row)
            await session.commit()
    except (SQLAlchemyError, Exception) as exc:  # noqa: BLE001 — informational
        logger.warning(
            "cost_tracker audit_events write failed (user=%s workload=%s): %r",
            user_id,
            workload,
            exc,
        )


__all__ = [
    "RATE_INPUT_PER_1K",
    "RATE_OUTPUT_PER_1K",
    "Workload",
    "compute_cost_inr",
    "get_daily_spend",
    "get_user_hourly_spend",
    "record",
]
