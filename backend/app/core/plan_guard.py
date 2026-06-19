"""Plan-based feature-budget enforcement.

Per BACKEND_ARCHITECTURE.md §4.E, this module owns the gate every
budget-incurring write-path consults BEFORE the DB write.

V1 limits (MVP_ARCH §10.7 + §10.9 free tier)
--------------------------------------------
======================  =====  ============  ============================
resource                limit  window        enforcement point
======================  =====  ============  ============================
product_count           50     total cap     catalog.service.create_product
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

Razorpay Wave 3 — tier-aware entitlement (Pricing v2 §5)
--------------------------------------------------------
Wave 3 extends the free-only gate into a tier-aware entitlement gate.

* :func:`resolve_entitlement` reads ``(users.plan, users.trial_ends_at, the
  user's subscriptions row)`` DB-FRESH (founder ruling F7 — NOT from the JWT
  claim) and collapses them to an :data:`EffectiveEntitlement`
  (``free | starter | pro | business``).  Annual cadences collapse to their
  base tier; LTD and the 14-day trial collapse to ``pro``; a paid entitlement
  ALWAYS wins over a still-live trial.
* :data:`_LIMITS_BY_ENTITLEMENT` carries the per-entitlement caps.  Free SKU
  cap is **50** per the founder ruling 2026-06-19 (PRICING_LOCKED v2 §5 —
  this CORRECTS the pre-existing live-code drift of 100).  Starter SKU cap is
  150; pro/business are UNLIMITED (the cap is skipped, not a sentinel).
* :func:`enforce_plan_limit` stays signature-compatible.  When a ``db`` session
  is available it resolves entitlement DB-fresh and gates on the resolved tier
  (option (a), F7).  When ``db`` is absent (the sliding-hour call sites that do
  not pass it today) it falls back to the caller-supplied ``plan`` arg — which
  is ``"free"`` at every live call site, so the free path is byte-for-byte
  unchanged and NO call-site churn is required.

V1.5 forward compat
-------------------
The JWT ``plan`` claim is NOT widened to carry the real tier (F7 rejects the
JWT-as-truth pattern).  Gating truth is always DB-fresh via
:func:`resolve_entitlement`.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
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

# ── Effective entitlement vocabulary (Razorpay Wave 3) ─────────────────────
#: The resolved feature-tier a user is entitled to RIGHT NOW.  This is a
#: SMALLER set than the Pricing v2 plan vocabulary: annual cadences and LTD and
#: the 14-day trial all collapse to their feature-equivalent here.
#:   plan 'starter'                         → "starter"
#:   plan 'pro' | 'pro_annual' | 'ltd'      → "pro"
#:   plan 'business' | 'business_annual'    → "business"
#:   plan 'free' + live trial               → "pro"
#:   plan 'free' (no/expired trial)         → "free"
EffectiveEntitlement = Literal["free", "starter", "pro", "business"]

#: plan-string → effective entitlement (annual/ltd collapse to base feature
#: tier).  ``free`` is handled specially (trial check) and is NOT in this map.
_PLAN_TO_ENTITLEMENT: dict[str, EffectiveEntitlement] = {
    "starter": "starter",
    "pro": "pro",
    "pro_annual": "pro",
    "ltd": "pro",
    "business": "business",
    "business_annual": "business",
}

#: Subscription ``status`` values that count as "currently entitled" (the paid
#: period is live).  A cancelled sub still entitles while
#: ``current_period_end`` is in the future — that is handled in the resolver,
#: not here.
_ACTIVE_SUB_STATUSES = frozenset({"active", "authenticated", "created", "completed"})

# (limit, window_seconds_or_None_for_total_cap)
V1_LIMITS_FREE: dict[str, tuple[int, int | None]] = {
    "product_count": (50, None),
    "ai_autofill_hourly": (50, 3600),
    "smart_picker_hourly": (100, 3600),
    "create_product_hourly": (20, 3600),
}

#: Sentinel for an UNLIMITED total-cap resource — the cap branch is SKIPPED
#: entirely when the limit is this value (never enforced), so no huge-number
#: sentinel can ever accidentally trip.
UNLIMITED: int | None = None  # only meaningful for total-cap resources

#: Per-effective-entitlement limit tables (Pricing v2 §5 + Q1/Q2 rulings).
#:
#:   free      → product_count 50  (founder ruling 2026-06-19; corrects the
#:               pre-existing live-code drift of 100)
#:   starter   → product_count 150; AI hourly == free floor (Q1: Starter→Pro
#:               difference is PURELY the SKU cap; do NOT tighten below free)
#:   pro       → product_count UNLIMITED; AI hourly == free floor (not tightened)
#:   business  → product_count UNLIMITED; AI hourly == free floor (not tightened)
#:
#: A value of ``("UNLIMITED", None)`` on ``product_count`` means the total-cap
#: gate is skipped for that entitlement.  The sliding-hour AI numbers are kept
#: at the existing free floor for paid tiers — PRICING_LOCKED does NOT enumerate
#: per-tier hourly AI limits, so per §7.G discipline we do NOT invent numbers;
#: paid tiers simply inherit the free floor (never tighter than free).
_PRODUCT_COUNT_UNLIMITED = "UNLIMITED"

_LIMITS_BY_ENTITLEMENT: dict[str, dict[str, tuple[int | str, int | None]]] = {
    "free": {
        "product_count": (50, None),
        "ai_autofill_hourly": (50, 3600),
        "smart_picker_hourly": (100, 3600),
        "create_product_hourly": (20, 3600),
    },
    "starter": {
        "product_count": (150, None),
        "ai_autofill_hourly": (50, 3600),
        "smart_picker_hourly": (100, 3600),
        "create_product_hourly": (20, 3600),
    },
    "pro": {
        "product_count": (_PRODUCT_COUNT_UNLIMITED, None),
        "ai_autofill_hourly": (50, 3600),
        "smart_picker_hourly": (100, 3600),
        "create_product_hourly": (20, 3600),
    },
    "business": {
        "product_count": (_PRODUCT_COUNT_UNLIMITED, None),
        "ai_autofill_hourly": (50, 3600),
        "smart_picker_hourly": (100, 3600),
        "create_product_hourly": (20, 3600),
    },
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


async def resolve_entitlement(
    *,
    user_id: UUID,
    db: AsyncSession,
) -> EffectiveEntitlement:
    """DB-FRESH effective-entitlement resolution (founder ruling F7).

    Reads ``users.plan`` + ``users.trial_ends_at`` + the user's latest
    ``subscriptions`` row (status, ``current_period_end``) and collapses them
    to an :data:`EffectiveEntitlement`.  This is the SINGLE source of truth for
    gating — it does NOT read the JWT ``plan`` claim (F7 rejects the
    JWT-as-truth pattern; the claim is hard-coded ``"free"`` at issue).

    Resolution order (paid entitlement ALWAYS wins over trial — §3.7):

    1. ``users.plan == 'ltd'``  → ``"pro"``  (perpetual; ``current_period_end``
       is the ``NULL`` sentinel for an LTD row but the plan column is the
       authority here).
    2. ``users.plan`` is a paid tier (``starter`` / ``pro`` / ``pro_annual`` /
       ``business`` / ``business_annual``) AND the user holds a currently
       entitled subscription (an ``active``/``authenticated``/``created`` sub,
       OR a ``cancelled`` sub whose ``current_period_end`` is still in the
       future) → the tier's collapsed entitlement.  Annual collapses to base.
       If the plan column is paid but NO sub is currently entitled (halted /
       expired / past period) → fall through to free (defensive — the
       webhook/sweep normally downgrades ``users.plan`` to ``free`` on halt).
    3. ``users.plan == 'free'`` AND ``trial_ends_at`` is set AND
       ``now() < trial_ends_at`` → ``"pro"``  (the 14-day app-side trial).
    4. ELSE → ``"free"``.

    Args:
        user_id: The authenticated principal to resolve.
        db: AsyncSession (REQUIRED — entitlement is read DB-fresh).

    Returns:
        The effective entitlement the user is owed right now.

    Raises:
        Nothing on a missing user — a vanished user resolves to ``"free"``
        (the gate fails closed to the least-privileged tier; the auth dep
        already 403s a vanished principal before any gated write).
    """
    # Local imports — keeps ``core/`` free of top-level ``app.shared.models``
    # imports beyond the audit/user dependencies already declared in §4.I.
    from app.shared.models import Subscription, User

    user = await db.get(User, user_id)
    if user is None:
        return "free"

    plan = user.plan
    now = datetime.now(timezone.utc)

    # 1 + 2 — paid plan column.  LTD is perpetual (no sub-period check needed).
    if plan in _PLAN_TO_ENTITLEMENT:
        if plan == "ltd":
            return "pro"

        # Look up the user's most-recent subscription row and decide whether it
        # currently entitles.
        stmt = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        sub = (await db.execute(stmt)).scalar_one_or_none()
        if sub is not None and _subscription_is_entitled(sub, now):
            return _PLAN_TO_ENTITLEMENT[plan]
        # Paid plan column but no live sub — defensive fall-through to free.
        logger.info(
            "resolve_entitlement: plan=%s but no currently-entitled sub for "
            "user=%s — falling back to free",
            plan,
            user_id,
        )
        return "free"

    # 3 — free plan with a live trial.
    if plan == "free" and user.trial_ends_at is not None:
        trial_end = user.trial_ends_at
        if trial_end.tzinfo is None:
            trial_end = trial_end.replace(tzinfo=timezone.utc)
        if now < trial_end:
            return "pro"

    # 4 — plain free.
    return "free"


def _subscription_is_entitled(sub: object, now: datetime) -> bool:
    """True if ``sub`` currently entitles its owner.

    Entitled when the status is one of the live-period statuses, OR the sub was
    cancelled but its ``current_period_end`` is still in the future (the seller
    paid for the remainder of the cycle).  An LTD row (``current_period_end IS
    NULL``) in an active status is perpetual and entitles.
    """
    status = getattr(sub, "status", None)
    period_end = getattr(sub, "current_period_end", None)

    if status in _ACTIVE_SUB_STATUSES:
        return True

    if status == "cancelled" and period_end is not None:
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=timezone.utc)
        return now < period_end

    return False


async def enforce_plan_limit(
    user_id: UUID,
    plan: str,
    resource: PlanResource,
    requested: int = 1,
    db: AsyncSession | None = None,
) -> None:
    """Fail-fast plan-limit gate, called BEFORE the budgeted write.

    Tier-aware per Razorpay Wave 3.  Entitlement is resolved DB-FRESH (F7)
    when a ``db`` session is available; otherwise it falls back to the
    caller-supplied ``plan`` arg (which is ``"free"`` at every live call site,
    so the free path is unchanged and NO call-site churn is required).

    Args:
        user_id: Caller's authenticated user_id.
        plan: Caller-supplied plan hint.  Used ONLY as a fallback when ``db``
            is not supplied (sliding-hour call sites that do not pass ``db``).
            When ``db`` is supplied the value is IGNORED in favour of the
            DB-fresh entitlement (F7 — plan read DB-fresh, not from the JWT).
        resource: One of the four V1 plan-budgeted resources.
        requested: Quantity being reserved.  Defaults to 1.
        db: AsyncSession.  REQUIRED when ``resource == "product_count"`` (the
            COUNT(*) source).  When supplied it ALSO drives DB-fresh entitlement
            resolution; when absent the ``plan`` arg is the fallback hint.

    Raises:
        PlanLimitExceededError: when the call would push the user past
            their entitlement's limit for the resource.
    """
    if resource not in V1_LIMITS_FREE:
        raise ValueError(
            f"enforce_plan_limit: unknown resource {resource!r} "
            f"(allowed: {sorted(V1_LIMITS_FREE.keys())})"
        )

    # Resolve the effective entitlement.  F7: DB-fresh when a session is
    # available; otherwise fall back to the caller's plan hint (free at every
    # live call site).
    if db is not None:
        entitlement: EffectiveEntitlement = await resolve_entitlement(
            user_id=user_id, db=db
        )
    else:
        entitlement = _coerce_plan_hint_to_entitlement(plan)

    limit_value, window = _LIMITS_BY_ENTITLEMENT[entitlement][resource]

    # UNLIMITED total-cap → skip the gate entirely (no sentinel that could trip).
    if limit_value == _PRODUCT_COUNT_UNLIMITED:
        return

    limit = int(limit_value)

    if window is None:
        await _enforce_total_cap(user_id, resource, limit, requested, db=db)
    else:
        await _enforce_sliding_window(user_id, resource, limit, window, requested)


def _coerce_plan_hint_to_entitlement(plan: str) -> EffectiveEntitlement:
    """Map a caller-supplied ``plan`` hint to an entitlement (no DB).

    Used only on the fallback path where ``db`` is unavailable.  An unknown
    or ``free`` hint resolves to ``"free"`` (least-privileged — fail closed).
    A trial is NOT detectable here (it needs ``trial_ends_at`` from the DB), so
    a free hint stays free; the DB-fresh path is the one that honours trials.
    """
    if plan == "ltd":
        return "pro"
    return _PLAN_TO_ENTITLEMENT.get(plan, "free")


__all__ = [
    "PlanResource",
    "EffectiveEntitlement",
    "V1_LIMITS_FREE",
    "PlanLimitExceededError",
    "resolve_entitlement",
    "enforce_plan_limit",
]
