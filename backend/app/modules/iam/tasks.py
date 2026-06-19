"""``iam`` Celery task bodies — Razorpay Wave 4 reconciliation + trial sweep.

Two periodic (Celery beat) sweep tasks owned by the ``iam`` module (which owns
billing / subscription state):

* ``billing.reconcile`` (every 6 hours) — lost/mis-ordered-webhook recovery.
  Pulls Razorpay's authoritative state via ``adapter.fetch_subscription`` for
  each non-terminal, Razorpay-backed subscription and converges local state
  using the SAME idempotent/monotonic guards as the webhook router (§0.4 of the
  Wave 4 task spec), PLUS a local-clock terminal sweep that downgrades
  ``cancelled``/``halted``/``completed`` subs past ``current_period_end`` to
  ``free`` (the eventual downgrade the cancelled webhook handler defers to this
  wave).
* ``billing.trial_expiry_sweep`` (daily 02:00 IST) — makes the 14-day app-side
  Pro trial → Free drop observable.  Finds ``free``-plan users whose
  ``trial_ends_at`` has passed and writes a ``billing.trial.expired`` audit row.
  NO Razorpay round-trip (the trial has no Razorpay object).

Why this file lives in ``modules/iam/`` (NOT ``workers/``)
---------------------------------------------------------
``BACKEND_ARCHITECTURE.md §3.I`` keeps ``app/workers/`` a canonical 2-file
subtree (``__init__.py`` + ``celery_app.py``); V1 task BODIES live in
``modules/<name>/tasks.py`` (e.g. ``image/tasks.py``, ``export/tasks.py``).
This module is the 3rd such task module (a §3.I/§18.B canonical-inventory bump,
founder-ratified 2026-06-19 for Razorpay Wave 4 — see ``BACKEND_ARCHITECTURE.md``
§3.I/§18.B amendment).  The ``beat_schedule`` + the ``include`` addition live in
``celery_app.py`` (the only module authorised to mutate the Celery app config).

Async-in-Celery pattern (§2 of the task spec — mirrors ``celery_app.py``)
-------------------------------------------------------------------------
Each Celery task is a SYNC function that runs ``asyncio.run(_*_async())`` over a
fresh :func:`app.shared.database.make_worker_session` (``NullPool``) session.
``AsyncSessionLocal`` is NEVER used in the worker (cross-loop bug — documented in
``shared/database.py``).  The async bodies accept an OPTIONAL ``session`` arg so
the integration tests can drive them directly with the rolled-back test session
(``await _reconcile_async(session)`` / ``await _trial_sweep_async(session)``)
without spinning a real worker.

Valkey singleton lock (§3.5 — mandatory regardless of deploy choice)
--------------------------------------------------------------------
Both tasks acquire a ``SET <key> <token> NX EX <ttl>`` advisory lock on Valkey
**DB 0** (the sessions/locks DB per ``CLAUDE.md``) at task start; if not acquired
the task no-ops with an INFO log (another pass is running / two beat processes).
The lock is released on completion (only by the holder, via a compare-and-delete
Lua script so a slow pass that lost its lock to TTL never deletes a newer
holder's lock).  This is belt-and-braces insurance against accidental
double-beat; the async bodies themselves are idempotent so a double-fire is
state-safe even without the lock.

No secrets / PII in logs (§2 / design §9)
-----------------------------------------
Logs carry Razorpay subscription ids, status strings, counts and durations
ONLY — never customer email / phone.  ``fetch_subscription`` is sufficient; the
reconcile never reads ``RazorpayCustomer``.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy import select

from app.adapters import RazorpayAdapterError
from app.adapters import razorpay as razorpay_adapter
from app.core.plan_guard import _subscription_is_entitled
from app.modules.iam.service import (
    _apply_period_monotonic,
    _downgrade_user_to_free,
    _epoch_to_utc,
    _grant_plan_for_sub,
)
from app.shared.database import make_worker_session
from app.shared.models.audit_event import AuditEvent
from app.shared.models.subscription import Subscription
from app.shared.models.user import User
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
#: Subscriptions that could still drift and are Razorpay-backed (Set 1, §3.3).
_NON_TERMINAL_STATUSES = (
    "created",
    "authenticated",
    "active",
    "past_due",
    "halted",
)

#: Terminal statuses whose paid period can lapse (Set 2 local-clock sweep, §3.3).
_TERMINAL_STATUSES = ("cancelled", "halted", "completed")

#: Razorpay subscription status → our local status (§3.1 — 1:1 overlap; an
#: unknown vendor status leaves the local status untouched, fail-safe).
_RZP_STATUS_TO_LOCAL: dict[str, str] = {
    "created": "created",
    "authenticated": "authenticated",
    "active": "active",
    "pending": "past_due",
    "halted": "halted",
    "cancelled": "cancelled",
    "completed": "completed",
    "expired": "completed",
    "paused": "past_due",
}

_RECONCILE_LOCK_KEY = "billing:reconcile:lock"
_TRIAL_SWEEP_LOCK_KEY = "billing:trial_sweep:lock"
#: TTL = a few × the expected pass duration (§3.5).  A sweep over the V1.5 sub
#: population finishes in well under this; the lock self-heals if a worker dies.
_LOCK_TTL_SECONDS = 600

#: Compare-and-delete: only release the lock if WE still hold it (token match),
#: so a pass that overran its TTL never deletes a newer holder's lock.
_RELEASE_LOCK_LUA = (
    "if redis.call('get', KEYS[1]) == ARGV[1] then "
    "return redis.call('del', KEYS[1]) else return 0 end"
)


# ─────────────────────────────────────────────────────────────────────────────
# Valkey singleton-lock helpers (§3.5) — DB 0 via shared.valkey
# ─────────────────────────────────────────────────────────────────────────────
async def _acquire_lock(key: str) -> tuple[Redis, str] | None:
    """Try to acquire a singleton advisory lock on Valkey DB 0.

    Returns ``(client, token)`` on success, ``None`` if another pass holds it.
    Lazy-imports the DB-0 client factory to keep module import light.
    """
    from app.shared.valkey import get_valkey_otp

    client = await get_valkey_otp()
    token = secrets.token_hex(16)
    acquired = await client.set(key, token, nx=True, ex=_LOCK_TTL_SECONDS)
    if not acquired:
        return None
    return client, token


async def _release_lock(client: Redis, key: str, token: str) -> None:
    """Release the lock iff we still hold it (compare-and-delete)."""
    try:
        await client.eval(_RELEASE_LOCK_LUA, 1, key, token)
    except Exception as exc:  # noqa: BLE001 — release is best-effort
        logger.warning("billing.lock release failed key=%s: %r", key, exc)


# ─────────────────────────────────────────────────────────────────────────────
# Part A — reconciliation (billing.reconcile)
# ─────────────────────────────────────────────────────────────────────────────
async def _fetch_non_terminal_razorpay_subs(session) -> list[Subscription]:
    """Set 1 query (§3.3): non-terminal, Razorpay-subscription-backed rows.

    Excludes LTD (``razorpay_subscription_id IS NULL`` / ``tier='ltd'`` — a
    one-time Orders purchase with no subscription object to fetch).
    """
    stmt = select(Subscription).where(
        Subscription.razorpay_subscription_id.is_not(None),
        Subscription.status.in_(_NON_TERMINAL_STATUSES),
        Subscription.tier != "ltd",
    )
    return list((await session.execute(stmt)).scalars().all())


async def _fetch_terminal_subs_past_period(session, now: datetime) -> list[Subscription]:
    """Set 2 query (§3.3): terminal subs whose paid period has ended."""
    stmt = select(Subscription).where(
        Subscription.status.in_(_TERMINAL_STATUSES),
        Subscription.current_period_end.is_not(None),
        Subscription.current_period_end < now,
    )
    return list((await session.execute(stmt)).scalars().all())


async def _reconcile_one(session, sub: Subscription, rzp) -> bool:
    """Converge one local sub to Razorpay's authoritative state (Set 1).

    Reuses the webhook transition guards: GREATEST monotonic period
    (``_apply_period_monotonic``), tier-grant (``_grant_plan_for_sub``),
    halted-downgrade (``_downgrade_user_to_free``).  NEVER re-activates a
    locally-``cancelled`` sub.  Returns True if any state changed (for counts).

    Idempotent: when local already equals Razorpay's truth, no write, no audit.
    """
    target = _RZP_STATUS_TO_LOCAL.get(rzp.status)
    if target is None:
        logger.info(
            "reconcile: unknown rzp status=%s sub=%s (skip)",
            rzp.status,
            sub.razorpay_subscription_id,
        )
        return False

    changed = False

    # 1. Monotonic period convergence (never rewind).
    before_period = sub.current_period_end
    _apply_period_monotonic(sub, _epoch_to_utc(rzp.current_end))
    if sub.current_period_end != before_period:
        changed = True

    # 2. Guarded status convergence.
    if sub.status == "cancelled":
        # A locally-cancelled sub stays cancelled even if Razorpay reports
        # otherwise (Set 2 handles its eventual downgrade).  Never re-activate.
        return changed

    if target in ("active", "authenticated") and sub.status != target:
        sub.status = "active" if target == "active" else target
        changed = True
        if target == "active":
            grant = await _grant_plan_for_sub(session, sub, event="billing.reconcile")
            if grant is not None:
                changed = True
    elif target == "halted" and sub.status != "halted":
        sub.status = "halted"
        changed = True
        down = await _downgrade_user_to_free(
            session, sub.user_id, reason="halted", event="billing.reconcile"
        )
        if down is not None:
            changed = True
    elif target in ("cancelled", "completed") and sub.status != target:
        sub.status = target
        changed = True
        # Downgrade is deferred to the Set-2 terminal sweep once the paid period
        # lapses (mirrors the cancelled webhook handler).

    return changed


async def _downgrade_if_no_other_entitlement(session, sub: Subscription, now: datetime) -> bool:
    """Set 2: downgrade the sub's user to ``free`` unless another sub entitles.

    Guard (§3.3): do NOT downgrade a user who holds a DIFFERENT currently-
    entitled subscription (e.g. they cancelled this one but upgraded into a new
    one).  Reuses the Wave 3 ``_subscription_is_entitled`` predicate.  Returns
    True if a downgrade was written.
    """
    other_stmt = select(Subscription).where(
        Subscription.user_id == sub.user_id,
        Subscription.id != sub.id,
    )
    others = (await session.execute(other_stmt)).scalars().all()
    if any(_subscription_is_entitled(o, now) for o in others):
        logger.info(
            "reconcile.sweep: user has another entitled sub — skip downgrade sub=%s",
            sub.razorpay_subscription_id or sub.id,
        )
        return False
    audit_id = await _downgrade_user_to_free(
        session, sub.user_id, reason="period_lapsed", event="billing.reconcile"
    )
    return audit_id is not None


async def _reconcile_async(session=None) -> dict[str, int]:
    """Reconciliation pass body (§3.4).

    Args:
        session: optional AsyncSession.  When provided (tests), the caller owns
            the transaction boundary; this body does NOT open its own session and
            does NOT commit (the rolled-back test session is reused).  When None
            (the Celery task), opens a worker session and commits per-sub.

    Returns a small counts dict for the caller / log line.
    """
    if session is not None:
        return await _reconcile_pass(session, owns_commit=False)
    async with make_worker_session() as worker_session:
        return await _reconcile_pass(worker_session, owns_commit=True)


async def _reconcile_pass(session, *, owns_commit: bool) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    set1 = 0
    converged = 0
    set2 = 0
    downgraded = 0

    # --- Set 1: Razorpay round-trip ---
    for sub in await _fetch_non_terminal_razorpay_subs(session):
        set1 += 1
        try:
            rzp = await razorpay_adapter.fetch_subscription(
                sub.razorpay_subscription_id  # type: ignore[arg-type]
            )
        except RazorpayAdapterError as exc:
            # Per-sub isolation (§3.4): one failure never aborts the pass.
            logger.warning(
                "reconcile: fetch failed sub=%s: %r (skip, retry next pass)",
                sub.razorpay_subscription_id,
                exc,
            )
            continue
        try:
            if await _reconcile_one(session, sub, rzp):
                converged += 1
                if owns_commit:
                    await session.commit()  # commit-per-sub (§3.4 resilience)
        except Exception as exc:  # noqa: BLE001 — per-sub isolation
            logger.warning(
                "reconcile: converge failed sub=%s: %r (rollback, continue)",
                sub.razorpay_subscription_id,
                exc,
            )
            if owns_commit:
                await session.rollback()

    # --- Set 2: local-clock terminal sweep ---
    for sub in await _fetch_terminal_subs_past_period(session, now):
        set2 += 1
        try:
            if await _downgrade_if_no_other_entitlement(session, sub, now):
                downgraded += 1
                if owns_commit:
                    await session.commit()
        except Exception as exc:  # noqa: BLE001 — per-sub isolation
            logger.warning(
                "reconcile.sweep: downgrade failed sub=%s: %r (rollback, continue)",
                sub.razorpay_subscription_id or sub.id,
                exc,
            )
            if owns_commit:
                await session.rollback()

    logger.info(
        "reconcile: done set1=%d converged=%d set2=%d downgraded=%d",
        set1,
        converged,
        set2,
        downgraded,
    )
    return {
        "set1": set1,
        "converged": converged,
        "set2": set2,
        "downgraded": downgraded,
    }


@celery_app.task(name="billing.reconcile")
def billing_reconcile() -> dict[str, int]:
    """Celery entrypoint (every 6h per beat_schedule) — §3.

    Acquires the Valkey singleton lock, then runs ``_reconcile_async`` over a
    worker session.  No-ops if another pass holds the lock.
    """
    async def _run() -> dict[str, int]:
        lock = await _acquire_lock(_RECONCILE_LOCK_KEY)
        if lock is None:
            logger.info("billing.reconcile: another pass holds the lock — no-op")
            return {"skipped": 1}
        client, token = lock
        try:
            return await _reconcile_async()
        finally:
            await _release_lock(client, _RECONCILE_LOCK_KEY, token)

    return asyncio.run(_run())


# ─────────────────────────────────────────────────────────────────────────────
# Part B — trial-expiry sweep (billing.trial_expiry_sweep)
# ─────────────────────────────────────────────────────────────────────────────
# R5 FINDING (verified 2026-06-19 against Wave 3 ``start_trial``,
# ``modules/iam/service.py``): the one-trial-per-phone 409 guard is keyed
# PRIMARILY on ``user.trial_ends_at is not None`` (past OR future).  After a
# trial expires the user reverts to ``plan='free'`` with NO subscription row, so
# the secondary guards (``plan != 'free'`` / existing-sub) do NOT cover the
# expired-trial case.  Therefore NULLING ``trial_ends_at`` WOULD RE-OPEN the
# trial.  Per §4.4 / §6 / R5 the sweep MUST NOT null ``trial_ends_at``; it uses
# an audit-row idempotency marker (a ``billing.trial.expired`` row already
# present for the user) instead.  No new column (Wave 1/3 own the schema).
# ─────────────────────────────────────────────────────────────────────────────
async def _user_already_swept(session, user_id) -> bool:
    """True if a ``billing.trial.expired`` audit row already exists for the user.

    Idempotency marker (R5): because the sweep does NOT null ``trial_ends_at``
    (that would re-open the once-per-phone trial), it instead skips any user who
    already has the expiry audit row so the notification fires exactly once.
    """
    stmt = (
        select(AuditEvent.id)
        .where(
            AuditEvent.user_id == user_id,
            AuditEvent.event_type == "billing.trial.expired",
        )
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def _fetch_expired_trial_users(session, now: datetime) -> list[User]:
    """§4.3 query: ``free``-plan users carrying an expired trial timestamp."""
    stmt = select(User).where(
        User.trial_ends_at.is_not(None),
        User.trial_ends_at < now,
        User.plan == "free",
    )
    return list((await session.execute(stmt)).scalars().all())


async def _trial_sweep_async(session=None) -> dict[str, int]:
    """Trial-expiry sweep body (§4.3).

    For each ``free`` user past ``trial_ends_at`` who has NOT already been swept,
    writes a ``billing.trial.expired`` business audit row.  ``users.plan`` is
    UNCHANGED (stays ``free`` — the trial granted entitlement via plan_guard,
    never a plan-string change).  ``trial_ends_at`` is deliberately NOT nulled
    (R5).  Idempotent via the audit-row marker.

    ``session`` semantics mirror :func:`_reconcile_async`.
    """
    if session is not None:
        return await _trial_sweep_pass(session, owns_commit=False)
    async with make_worker_session() as worker_session:
        return await _trial_sweep_pass(worker_session, owns_commit=True)


async def _trial_sweep_pass(session, *, owns_commit: bool) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    from app.modules.iam.service import _audit_business_effect

    candidates = 0
    expired = 0
    for user in await _fetch_expired_trial_users(session, now):
        candidates += 1
        try:
            if await _user_already_swept(session, user.id):
                continue
            await _audit_business_effect(
                session,
                user_id=user.id,
                event_type="billing.trial.expired",
                metadata={"reason": "trial_ended"},
            )
            expired += 1
            if owns_commit:
                await session.commit()
        except Exception as exc:  # noqa: BLE001 — per-user isolation
            logger.warning(
                "trial_sweep: fire failed user=%s: %r (rollback, continue)",
                user.id,
                exc,
            )
            if owns_commit:
                await session.rollback()

    logger.info(
        "trial_sweep: done candidates=%d expired=%d", candidates, expired
    )
    return {"candidates": candidates, "expired": expired}


@celery_app.task(name="billing.trial_expiry_sweep")
def billing_trial_expiry_sweep() -> dict[str, int]:
    """Celery entrypoint (daily 02:00 IST per beat_schedule) — §4.

    Acquires the Valkey singleton lock, then runs ``_trial_sweep_async`` over a
    worker session.  No-ops if another pass holds the lock.
    """
    async def _run() -> dict[str, int]:
        lock = await _acquire_lock(_TRIAL_SWEEP_LOCK_KEY)
        if lock is None:
            logger.info(
                "billing.trial_expiry_sweep: another pass holds the lock — no-op"
            )
            return {"skipped": 1}
        client, token = lock
        try:
            return await _trial_sweep_async()
        finally:
            await _release_lock(client, _TRIAL_SWEEP_LOCK_KEY, token)

    return asyncio.run(_run())


__all__ = [
    "billing_reconcile",
    "billing_trial_expiry_sweep",
    "_reconcile_async",
    "_trial_sweep_async",
]
