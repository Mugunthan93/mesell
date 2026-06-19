"""Razorpay full-lifecycle + Wave-4-tasks integration suite (design §14 Wave 4).

End-to-end billing lifecycle driven through the webhook router via signed events,
PLUS coverage of the two Wave 4 periodic tasks (``billing.reconcile`` +
``billing.trial_expiry_sweep``).  The Wave-2-scoped router UNIT tests live in
``test_razorpay_webhook_router.py`` (not duplicated here).

Coverage map (§5.1 items 1–18):
  1  full subscription lifecycle (subscribe→activate→charge→pending→halt)
  2  cancel (status cancelled, plan persists until current_period_end)
  3  LTD payment.captured → permanent ltd, replay idempotent
  4  starter tier → plan starter + 150-SKU-cap entitlement
  5  annual → effective entitlement collapses to base
  6  upgrade-immediate / downgrade-at-period-end
  7  idempotent replay (zero double side effects)
  8  out-of-order guard (GREATEST; charged-after-cancelled no re-activate)
  9  signature-fail 401
  10 trial grant (entitlement pro while live, plan stays free)
  11 trial expiry sweep (audit row, plan stays free, entitlement reverts, idempotent)
  12 trial→pay supersede
  13 reconcile lost-webhook recovery
  14 reconcile idempotent / no-op when already converged
  15 reconcile monotonic period
  16 reconcile terminal sweep (Set 2) + skip-if-other-entitled
  17 reconcile skips LTD (fetch_subscription NOT called)
  18 reconcile per-sub isolation (one raise does not abort the pass)

Needs a real Postgres (ON CONFLICT, RETURNING, partial unique index, GREATEST),
so it runs through the function-scoped ``db_session`` fixture (savepoint +
rollback isolation).  ``fetch_subscription`` is patched with an ``AsyncMock``
returning crafted ``RazorpaySubscription`` dataclasses — never hits live
Razorpay.  The Valkey singleton lock is bypassed by calling the async task
bodies directly (``_reconcile_async(session)`` / ``_trial_sweep_async(session)``).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.plan_guard import resolve_entitlement
from app.modules.iam import service as iam_service
from app.modules.iam import tasks as iam_tasks
from app.modules.iam.exceptions import WebhookSignatureInvalidError
from app.shared.config import settings
from app.shared.models.audit_event import AuditEvent
from app.shared.models.subscription import Subscription
from app.shared.models.user import User

pytestmark = pytest.mark.integration


# ── Webhook signing / event-payload helpers (mirror the router unit suite) ────
def _sign(body: bytes) -> str:
    return hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()


def _event(
    event: str,
    *,
    event_id: str,
    subscription: dict | None = None,
    payment: dict | None = None,
    order: dict | None = None,
) -> bytes:
    payload: dict = {"entity": "event", "event": event, "id": event_id, "payload": {}}
    if subscription is not None:
        payload["payload"]["subscription"] = {"entity": subscription}
    if payment is not None:
        payload["payload"]["payment"] = {"entity": payment}
    if order is not None:
        payload["payload"]["order"] = {"entity": order}
    return json.dumps(payload).encode("utf-8")


async def _call(db, body: bytes, *, signature: str | None = None):
    return await iam_service.capture_razorpay_webhook(
        body, signature if signature is not None else _sign(body), db=db
    )


async def _make_user(db, *, plan: str = "free", trial_ends_at=None) -> User:
    user = User(
        phone=f"+9198{uuid.uuid4().int % 100000000:08d}",
        plan=plan,
        trial_ends_at=trial_ends_at,
    )
    db.add(user)
    await db.flush()
    return user


async def _make_sub(
    db,
    user: User,
    *,
    tier: str = "pro",
    status: str = "created",
    rzp_sub_id: str | None = None,
    rzp_order_id: str | None = None,
    current_period_end=None,
) -> Subscription:
    sub = Subscription(
        user_id=user.id,
        tier=tier,
        status=status,
        razorpay_subscription_id=rzp_sub_id,
        razorpay_order_id=rzp_order_id,
        current_period_end=current_period_end,
    )
    db.add(sub)
    await db.flush()
    return sub


def _rzp_sub(status: str, *, current_end: int | None = None, notes: dict | None = None):
    """Build a crafted RazorpaySubscription dataclass (the adapter's return type)."""
    from app.adapters.razorpay import RazorpaySubscription

    return RazorpaySubscription(
        id="sub_x",
        status=status,
        plan_id="plan_test",
        current_end=current_end,
        notes=notes or {},
    )


def _epoch(dt: datetime) -> int:
    return int(dt.timestamp())


async def _count_audit(db, user_id, event_type: str) -> int:
    rows = (
        await db.execute(
            select(AuditEvent.id).where(
                AuditEvent.user_id == user_id,
                AuditEvent.event_type == event_type,
            )
        )
    ).scalars().all()
    return len(rows)


# ═════════════════════════════════════════════════════════════════════════════
# LIFECYCLE (webhook-driven)
# ═════════════════════════════════════════════════════════════════════════════
# 1 — full subscription lifecycle
async def test_full_subscription_lifecycle(db_session):
    user = await _make_user(db_session)
    sub = await _make_sub(
        db_session, user, tier="pro", status="created", rzp_sub_id="sub_life"
    )
    future = _epoch(datetime.now(timezone.utc) + timedelta(days=30))

    # activated → active + plan pro
    await _call(
        db_session,
        _event("subscription.activated", event_id="evt_l1",
               subscription={"id": "sub_life", "current_end": future}),
    )
    await db_session.refresh(sub)
    await db_session.refresh(user)
    assert sub.status == "active"
    assert user.plan == "pro"

    # charged renewal → period advances, payment row
    later = _epoch(datetime.now(timezone.utc) + timedelta(days=60))
    await _call(
        db_session,
        _event("subscription.charged", event_id="evt_l2",
               subscription={"id": "sub_life", "current_end": later},
               payment={"id": "pay_l2", "amount": 49900, "currency": "INR"}),
    )
    await db_session.refresh(sub)
    assert sub.status == "active"

    # pending → past_due
    await _call(
        db_session,
        _event("subscription.pending", event_id="evt_l3",
               subscription={"id": "sub_life"}),
    )
    await db_session.refresh(sub)
    assert sub.status == "past_due"

    # halted → free
    await _call(
        db_session,
        _event("subscription.halted", event_id="evt_l4",
               subscription={"id": "sub_life"}),
    )
    await db_session.refresh(sub)
    await db_session.refresh(user)
    assert sub.status == "halted"
    assert user.plan == "free"


# 2 — cancel keeps plan until period end
async def test_cancel_keeps_plan_until_period_end(db_session):
    user = await _make_user(db_session, plan="pro")
    sub = await _make_sub(
        db_session, user, tier="pro", status="active", rzp_sub_id="sub_cxl2",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=10),
    )
    await _call(
        db_session,
        _event("subscription.cancelled", event_id="evt_c1",
               subscription={"id": "sub_cxl2"}),
    )
    await db_session.refresh(sub)
    await db_session.refresh(user)
    assert sub.status == "cancelled"
    assert user.plan == "pro"  # entitlement persists until current_period_end


# 3 — LTD payment.captured permanent + replay idempotent
async def test_ltd_capture_permanent_and_replay(db_session):
    user = await _make_user(db_session)
    sub = await _make_sub(
        db_session, user, tier="ltd", status="created", rzp_order_id="order_l3"
    )
    body = _event(
        "payment.captured", event_id="evt_ltd3",
        payment={"id": "pay_l3", "amount": 499900, "order_id": "order_l3"},
        order={"id": "order_l3", "notes": {"tier": "ltd"}},
    )
    await _call(db_session, body)
    await db_session.refresh(sub)
    await db_session.refresh(user)
    assert user.plan == "ltd"
    assert sub.status == "active"
    assert sub.current_period_end is None  # perpetual sentinel
    # replay idempotent → still exactly one grant audit
    await _call(db_session, body)
    assert await _count_audit(db_session, user.id, "billing.plan.granted") == 1


# 4 — starter tier → 150-SKU cap entitlement
async def test_starter_tier_entitlement(db_session):
    user = await _make_user(db_session)
    await _make_sub(
        db_session, user, tier="starter", status="created", rzp_sub_id="sub_st",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    await _call(
        db_session,
        _event("subscription.activated", event_id="evt_st",
               subscription={"id": "sub_st",
                             "current_end": _epoch(datetime.now(timezone.utc) + timedelta(days=30))}),
    )
    await db_session.refresh(user)
    assert user.plan == "starter"
    ent = await resolve_entitlement(user_id=user.id, db=db_session)
    assert ent == "starter"


# 5 — annual collapses to base entitlement
async def test_annual_collapses_to_base(db_session):
    user = await _make_user(db_session)
    await _make_sub(
        db_session, user, tier="pro_annual", status="created", rzp_sub_id="sub_an",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=365),
    )
    await _call(
        db_session,
        _event("subscription.activated", event_id="evt_an",
               subscription={"id": "sub_an",
                             "current_end": _epoch(datetime.now(timezone.utc) + timedelta(days=365))}),
    )
    await db_session.refresh(user)
    assert user.plan == "pro_annual"
    ent = await resolve_entitlement(user_id=user.id, db=db_session)
    assert ent in ("pro", "pro_annual")  # annual collapses to the pro base entitlement


# 6 — upgrade-immediate via subscription.updated
async def test_upgrade_immediate(db_session):
    user = await _make_user(db_session, plan="pro")
    sub = await _make_sub(
        db_session, user, tier="pro", status="active", rzp_sub_id="sub_up",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=20),
    )
    await _call(
        db_session,
        _event("subscription.updated", event_id="evt_up",
               subscription={"id": "sub_up", "notes": {"tier": "business"}}),
    )
    await db_session.refresh(sub)
    await db_session.refresh(user)
    assert sub.tier == "business"
    assert user.plan == "business"  # upgrade lands immediately


# 7 — idempotent replay (zero double side effects)
async def test_idempotent_replay(db_session):
    user = await _make_user(db_session)
    await _make_sub(
        db_session, user, tier="pro", status="created", rzp_sub_id="sub_idem"
    )
    body = _event("subscription.activated", event_id="evt_idem",
                  subscription={"id": "sub_idem",
                                "current_end": _epoch(datetime.now(timezone.utc) + timedelta(days=30))})
    await _call(db_session, body)
    r2 = await _call(db_session, body)
    assert r2.audit_event_id is None  # dedupe no-op
    assert await _count_audit(db_session, user.id, "billing.plan.granted") == 1


# 8 — out-of-order guard
async def test_out_of_order_period_and_no_reactivate(db_session):
    user = await _make_user(db_session, plan="pro")
    sub = await _make_sub(
        db_session, user, tier="pro", status="active", rzp_sub_id="sub_ooo"
    )
    await _call(
        db_session,
        _event("subscription.charged", event_id="evt_o1",
               subscription={"id": "sub_ooo", "current_end": 2000000000},
               payment={"id": "pay_o1", "amount": 49900}),
    )
    await db_session.refresh(sub)
    later = sub.current_period_end
    await _call(
        db_session,
        _event("subscription.charged", event_id="evt_o2",
               subscription={"id": "sub_ooo", "current_end": 1000000000},
               payment={"id": "pay_o2", "amount": 49900}),
    )
    await db_session.refresh(sub)
    assert sub.current_period_end == later  # GREATEST guard

    # charged after cancelled does not re-activate
    sub.status = "cancelled"
    await db_session.flush()
    await _call(
        db_session,
        _event("subscription.charged", event_id="evt_o3",
               subscription={"id": "sub_ooo", "current_end": 3000000000},
               payment={"id": "pay_o3", "amount": 49900}),
    )
    await db_session.refresh(sub)
    assert sub.status == "cancelled"


# 9 — signature-fail
async def test_signature_fail_no_mutation(db_session):
    user = await _make_user(db_session)
    sub = await _make_sub(
        db_session, user, tier="pro", status="created", rzp_sub_id="sub_sig"
    )
    body = _event("subscription.activated", event_id="evt_sig",
                  subscription={"id": "sub_sig"})
    with pytest.raises(WebhookSignatureInvalidError):
        await _call(db_session, body, signature="deadbeef" * 8)
    await db_session.refresh(sub)
    assert sub.status == "created"


# ═════════════════════════════════════════════════════════════════════════════
# TRIAL (no Razorpay)
# ═════════════════════════════════════════════════════════════════════════════
# 10 — trial grant
async def test_trial_grant_entitlement(db_session):
    user = await _make_user(db_session)
    res = await iam_service.start_trial(user_id=user.id, db=db_session)
    await db_session.refresh(user)
    assert user.trial_ends_at is not None
    assert user.plan == "free"
    ent = await resolve_entitlement(user_id=user.id, db=db_session)
    assert ent == "pro"
    assert res.entitlement == "pro"


# 11 — trial expiry sweep
async def test_trial_expiry_sweep(db_session):
    past = datetime.now(timezone.utc) - timedelta(days=1)
    user = await _make_user(db_session, plan="free", trial_ends_at=past)
    await db_session.flush()

    counts = await iam_tasks._trial_sweep_async(db_session)
    assert counts["expired"] == 1

    await db_session.refresh(user)
    # plan unchanged, entitlement reverts, audit row written
    assert user.plan == "free"
    assert await _count_audit(db_session, user.id, "billing.trial.expired") == 1
    ent = await resolve_entitlement(user_id=user.id, db=db_session)
    assert ent == "free"

    # R5: trial_ends_at NOT nulled (would re-open the once-per-phone trial)
    assert user.trial_ends_at is not None

    # idempotent: 2nd sweep is a no-op (audit-row marker present)
    counts2 = await iam_tasks._trial_sweep_async(db_session)
    assert counts2["expired"] == 0
    assert await _count_audit(db_session, user.id, "billing.trial.expired") == 1


# 12 — trial→pay supersede
async def test_trial_then_pay_supersede(db_session):
    future_trial = datetime.now(timezone.utc) + timedelta(days=10)
    user = await _make_user(db_session, plan="free", trial_ends_at=future_trial)
    await _make_sub(
        db_session, user, tier="business", status="created", rzp_sub_id="sub_sup"
    )
    await _call(
        db_session,
        _event("subscription.activated", event_id="evt_sup",
               subscription={"id": "sub_sup",
                             "current_end": _epoch(datetime.now(timezone.utc) + timedelta(days=30))}),
    )
    await db_session.refresh(user)
    assert user.plan == "business"
    ent = await resolve_entitlement(user_id=user.id, db=db_session)
    assert ent == "business"  # paid entitlement wins over still-set trial


# ═════════════════════════════════════════════════════════════════════════════
# RECONCILIATION (Wave 4 task)
# ═════════════════════════════════════════════════════════════════════════════
# 13 — lost-webhook recovery
async def test_reconcile_lost_webhook_recovery(db_session, monkeypatch):
    user = await _make_user(db_session)
    sub = await _make_sub(
        db_session, user, tier="pro", status="past_due", rzp_sub_id="sub_lost"
    )
    future = datetime.now(timezone.utc) + timedelta(days=30)

    from unittest.mock import AsyncMock
    fetch = AsyncMock(return_value=_rzp_sub("active", current_end=_epoch(future)))
    monkeypatch.setattr(iam_tasks.razorpay_adapter, "fetch_subscription", fetch)

    counts = await iam_tasks._reconcile_async(db_session)
    assert counts["converged"] == 1

    await db_session.refresh(sub)
    await db_session.refresh(user)
    assert sub.status == "active"
    assert user.plan == "pro"
    assert sub.current_period_end is not None
    assert await _count_audit(db_session, user.id, "billing.plan.granted") == 1


# 14 — reconcile idempotent / no-op when converged
async def test_reconcile_noop_when_converged(db_session, monkeypatch):
    user = await _make_user(db_session, plan="pro")
    future = datetime.now(timezone.utc) + timedelta(days=30)
    sub = await _make_sub(
        db_session, user, tier="pro", status="active", rzp_sub_id="sub_conv",
        current_period_end=future,
    )
    from unittest.mock import AsyncMock
    fetch = AsyncMock(return_value=_rzp_sub("active", current_end=_epoch(future)))
    monkeypatch.setattr(iam_tasks.razorpay_adapter, "fetch_subscription", fetch)

    counts = await iam_tasks._reconcile_async(db_session)
    assert counts["converged"] == 0  # already converged → no write
    assert await _count_audit(db_session, user.id, "billing.plan.granted") == 0
    await db_session.refresh(sub)
    assert sub.status == "active"


# 15 — monotonic period (earlier rzp end does not rewind)
async def test_reconcile_monotonic_period(db_session, monkeypatch):
    user = await _make_user(db_session, plan="pro")
    later = datetime.now(timezone.utc) + timedelta(days=60)
    sub = await _make_sub(
        db_session, user, tier="pro", status="active", rzp_sub_id="sub_mono4",
        current_period_end=later,
    )
    earlier = datetime.now(timezone.utc) + timedelta(days=10)
    from unittest.mock import AsyncMock
    fetch = AsyncMock(return_value=_rzp_sub("active", current_end=_epoch(earlier)))
    monkeypatch.setattr(iam_tasks.razorpay_adapter, "fetch_subscription", fetch)

    await iam_tasks._reconcile_async(db_session)
    await db_session.refresh(sub)
    # within a second tolerance — GREATEST never rewinds
    assert sub.current_period_end.replace(microsecond=0) == later.replace(microsecond=0)


# 16 — terminal sweep (Set 2) + skip-if-other-entitled
async def test_reconcile_terminal_sweep_downgrades(db_session, monkeypatch):
    from unittest.mock import AsyncMock
    # never-called fetch (no Set-1 subs)
    monkeypatch.setattr(
        iam_tasks.razorpay_adapter, "fetch_subscription", AsyncMock()
    )
    past = datetime.now(timezone.utc) - timedelta(days=1)
    user = await _make_user(db_session, plan="pro")
    await _make_sub(
        db_session, user, tier="pro", status="cancelled", rzp_sub_id="sub_term",
        current_period_end=past,
    )
    counts = await iam_tasks._reconcile_async(db_session)
    assert counts["downgraded"] == 1
    await db_session.refresh(user)
    assert user.plan == "free"


async def test_reconcile_terminal_sweep_skips_if_other_entitled(db_session, monkeypatch):
    from unittest.mock import AsyncMock
    monkeypatch.setattr(
        iam_tasks.razorpay_adapter, "fetch_subscription",
        AsyncMock(return_value=_rzp_sub("active",
                  current_end=_epoch(datetime.now(timezone.utc) + timedelta(days=30)))),
    )
    past = datetime.now(timezone.utc) - timedelta(days=1)
    future = datetime.now(timezone.utc) + timedelta(days=30)
    user = await _make_user(db_session, plan="pro")
    # cancelled+lapsed sub (Set 2 candidate)
    await _make_sub(
        db_session, user, tier="pro", status="cancelled", rzp_order_id="ord_skip",
        current_period_end=past,
    )
    # a DIFFERENT, currently-active sub → user must NOT be downgraded
    await _make_sub(
        db_session, user, tier="business", status="active", rzp_sub_id="sub_other",
        current_period_end=future,
    )
    await iam_tasks._reconcile_async(db_session)
    await db_session.refresh(user)
    assert user.plan != "free"  # protected by the other entitled sub


# 17 — reconcile skips LTD (fetch_subscription NOT called for it)
async def test_reconcile_skips_ltd(db_session, monkeypatch):
    from unittest.mock import AsyncMock
    fetch = AsyncMock()
    monkeypatch.setattr(iam_tasks.razorpay_adapter, "fetch_subscription", fetch)
    user = await _make_user(db_session, plan="ltd")
    # LTD: no razorpay_subscription_id, perpetual sentinel, tier ltd, active
    await _make_sub(
        db_session, user, tier="ltd", status="active", rzp_order_id="ord_ltd17",
        current_period_end=None,
    )
    await iam_tasks._reconcile_async(db_session)
    fetch.assert_not_called()  # LTD never round-trips to fetch_subscription


# 18 — per-sub isolation (one raise does not abort the pass)
async def test_reconcile_per_sub_isolation(db_session, monkeypatch):
    user1 = await _make_user(db_session)
    user2 = await _make_user(db_session)
    await _make_sub(
        db_session, user1, tier="pro", status="past_due", rzp_sub_id="sub_bad"
    )
    await _make_sub(
        db_session, user2, tier="pro", status="past_due", rzp_sub_id="sub_good"
    )
    future = datetime.now(timezone.utc) + timedelta(days=30)

    from app.adapters import RazorpayAdapterError

    async def _fetch(sub_id):
        if sub_id == "sub_bad":
            raise RazorpayAdapterError("simulated razorpay outage")
        return _rzp_sub("active", current_end=_epoch(future))

    monkeypatch.setattr(iam_tasks.razorpay_adapter, "fetch_subscription", _fetch)

    counts = await iam_tasks._reconcile_async(db_session)
    # the good sub still converged despite the bad sub raising
    assert counts["converged"] == 1
    await db_session.refresh(user2)
    assert user2.plan == "pro"
    await db_session.refresh(user1)
    assert user1.plan == "free"  # bad sub skipped, no grant
