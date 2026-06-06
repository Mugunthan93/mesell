"""Plan-based feature-budget enforcement.

Per BACKEND_ARCHITECTURE.md §4.E, this module owns the gate every
budget-incurring write-path consults BEFORE the DB write.

V1 limits (MVP_ARCH §10.7 + §10.9 free tier)
--------------------------------------------
======================  =====  ============  ============================
resource                limit  window        enforcement point
======================  =====  ============  ============================
product_count           100    total cap     catalog.service.create_product
ai_autofill_hourly      50     sliding-hour  catalog.service.autofill_product
smart_picker_hourly     100    sliding-hour  category.service.suggest
create_product_hourly   20     sliding-hour  catalog.service.create_product
======================  =====  ============  ============================

OTP rate limit (3/h/phone) is **NOT** here — it is a security limit
enforced by ``rate_limit_mw`` per §1.F ("security before business").

product_count storage decision (FLAGGED)
----------------------------------------
``product_count`` is a TOTAL cap, not a sliding-window counter, so the
authoritative source is ``SELECT COUNT(*) FROM products WHERE user_id = ?``.
That requires an ``AsyncSession``.  Rather than wire a Valkey-counter that
the catalog service must keep in sync (extra failure mode), this function
accepts an optional ``db: AsyncSession`` keyword arg and queries directly
when ``resource == "product_count"``.  Callers that hit this resource MUST
pass ``db``.

V1.5 forward compat
-------------------
``plan`` is accepted but only ``"free"`` is dispatched in V1.  When the
tier widens to ``"free" | "pro"`` per MVP_ARCH §14, this module branches
on the value; callers do not change.
"""

from __future__ import annotations

import logging
import time
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import MeesellError
from app.shared.valkey import get_valkey_otp

logger = logging.getLogger(__name__)

# ── Locked resource catalogue ──────────────────────────────────────────────
PlanResource = Literal[
    "product_count",
    "ai_autofill_hourly",
    "smart_picker_hourly",
    "create_product_hourly",
]

# (limit, window_seconds_or_None_for_total_cap)
V1_LIMITS_FREE: dict[str, tuple[int, int | None]] = {
    "product_count": (100, None),
    "ai_autofill_hourly": (50, 3600),
    "smart_picker_hourly": (100, 3600),
    "create_product_hourly": (20, 3600),
}


class PlanLimitExceededError(MeesellError):
    """Raised when a feature-budget gate refuses a write.

    Status 402 (Payment Required) — the resource is real, the auth is fine,
    but the plan's quota is exhausted.  ``validation_message_id`` =
    ``"plan.limit_exceeded"``.

    Attributes:
        resource: Which budget tripped.
        current: Value at time of refusal.
        limit: Plan cap.
    """

    code = "plan.limit_exceeded"
    status_code = 402
    validation_message_id = "plan.limit_exceeded"

    def __init__(self, resource: str, current: int, limit: int) -> None:
        self.resource = resource
        self.current = current
        self.limit = limit
        super().__init__(
            detail=(
                f"Plan limit exceeded: {resource} at {current}/{limit} "
                "(upgrade your plan or wait for the window to reset)."
            )
        )


def _hourly_key(user_id: UUID, resource: str) -> str:
    """Sliding-window sorted-set key in Valkey DB 0."""
    return f"plan:{user_id}:{resource}"


async def _enforce_sliding_window(
    user_id: UUID,
    resource: str,
    limit: int,
    window: int,
    requested: int,
) -> None:
    """Sliding-window counter — same primitive as ``rate_limit_mw``."""
    client = await get_valkey_otp()
    key = _hourly_key(user_id, resource)
    now = time.time()
    cutoff = now - window

    # Trim expired entries + count.
    async with client.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(key, 0, cutoff)
        pipe.zcard(key)
        results = await pipe.execute()
    current = int(results[1])

    if current + requested > limit:
        raise PlanLimitExceededError(resource=resource, current=current, limit=limit)

    # Reserve the slot(s).  Add ``requested`` distinct members — each carries
    # the same score so the trim works on all of them at expiry time.
    async with client.pipeline(transaction=True) as pipe:
        for i in range(requested):
            member = f"{now}:{i}:{int(now * 1_000_000) % 1_000_000}"
            pipe.zadd(key, {member: now})
        pipe.expire(key, window)
        await pipe.execute()


async def _enforce_total_cap(
    user_id: UUID,
    resource: str,
    limit: int,
    requested: int,
    db: AsyncSession | None,
) -> None:
    """Total-cap counter — single COUNT(*) query.

    Only ``product_count`` uses this path in V1.  ``db`` MUST be supplied.
    """
    if db is None:
        raise ValueError(
            f"enforce_plan_limit({resource}=total cap) requires db kwarg "
            "(SELECT COUNT(*) is the authoritative source)"
        )
    # Local import — keeps ``core/`` free of top-level ``app.shared.models``
    # imports beyond the audit/user dependencies already declared in §4.I.
    from app.shared.models import Product

    stmt = (
        select(func.count(Product.id))
        .where(Product.user_id == user_id)
        .where(Product.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    current = int(result.scalar_one() or 0)

    if current + requested > limit:
        raise PlanLimitExceededError(resource=resource, current=current, limit=limit)


async def enforce_plan_limit(
    user_id: UUID,
    plan: str,
    resource: PlanResource,
    requested: int = 1,
    db: AsyncSession | None = None,
) -> None:
    """Fail-fast plan-limit gate, called BEFORE the budgeted write.

    Args:
        user_id: Caller's authenticated user_id.
        plan: JWT ``plan`` claim.  V1 only ``"free"`` is recognised;
            unknown values fall through to ``free`` limits.
        resource: One of the four V1 plan-budgeted resources.
        requested: Quantity being reserved.  Defaults to 1.
        db: AsyncSession.  REQUIRED when ``resource == "product_count"``;
            ignored for sliding-hour resources.

    Raises:
        PlanLimitExceededError: when the call would push the user past
            their plan's limit for the resource.
    """
    if plan != "free":
        logger.info(
            "enforce_plan_limit: plan=%s not recognised in V1, falling back to free",
            plan,
        )

    if resource not in V1_LIMITS_FREE:
        raise ValueError(
            f"enforce_plan_limit: unknown resource {resource!r} "
            f"(allowed: {sorted(V1_LIMITS_FREE.keys())})"
        )

    limit, window = V1_LIMITS_FREE[resource]

    if window is None:
        await _enforce_total_cap(user_id, resource, limit, requested, db=db)
    else:
        await _enforce_sliding_window(user_id, resource, limit, window, requested)


__all__ = [
    "PlanResource",
    "V1_LIMITS_FREE",
    "PlanLimitExceededError",
    "enforce_plan_limit",
]
