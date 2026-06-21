"""Wave-2 webhook event-router tests (RAZORPAY_INTEGRATION_SPEC §4; task spec §7).

Exercises the idempotent, out-of-order-tolerant Razorpay webhook router in
``app.modules.iam.service.capture_razorpay_webhook``:

* signature gate (401) + malformed payload (400)
* happy-path grant (subscription.activated)
* idempotent replay (ON CONFLICT (event_id) DO NOTHING) — the headline test
* atomic rollback (dedupe insert + mutation are one transaction)
* out-of-order period guard (GREATEST monotonicity; cancelled not re-activated)
* LTD payment.captured path (perpetual sentinel)
* renewal heartbeat (subscription.charged)
* halt downgrade (users.plan='free')
* unknown event type → recorded + 200 + no dispatch

These tests need a real Postgres (ON CONFLICT, RETURNING, partial unique index),
so they run through the function-scoped ``db_session`` fixture (savepoint +
rollback isolation).  Webhook payloads are HMAC-signed with the test
``RAZORPAY_WEBHOOK_SECRET`` so ``verify_webhook_signature`` passes.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import pytest
from sqlalchemy import select

from app.modules.iam import service as iam_service
from app.modules.iam.exceptions import (
    MalformedWebhookPayloadError,
    WebhookSignatureInvalidError,
)
from app.shared.config import settings
from app.shared.models.audit_event import AuditEvent
from app.shared.models.payment import Payment
from app.shared.models.subscription import Subscription
from app.shared.models.user import User
from app.shared.models.webhook_event import WebhookEvent

pytestmark = pytest.mark.integration


# ── Helpers ─────────────────────────────────────────────────────────────────
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
    refund: dict | None = None,
) -> bytes:
    payload: dict = {"entity": "event", "event": event, "id": event_id, "payload": {}}
    if subscription is not None:
        payload["payload"]["subscription"] = {"entity": subscription}
    if payment is not None:
        payload["payload"]["payment"] = {"entity": payment}
    if order is not None:
        payload["payload"]["order"] = {"entity": order}
    if refund is not None:
        payload["payload"]["refund"] = {"entity": refund}
    return json.dumps(payload).encode("utf-8")


async def _make_user(db, *, plan: str = "free") -> User:
    user = User(phone=f"+9198{uuid.uuid4().int % 100000000:08d}", plan=plan)
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


async def _call(db, body: bytes, *, signature: str | None = None):
    return await iam_service.capture_razorpay_webhook(
        body, signature if signature is not None else _sign(body), db=db
    )


# ── 1. Signature gate ───────────────────────────────────────────────────────
async def test_bad_signature_raises_401_and_no_state_change(db_session):
    body = _event(
        "subscription.activated", event_id="evt_badsig",
        subscription={"id": "sub_x"},
    )
    with pytest.raises(WebhookSignatureInvalidError):
        await _call(db_session, body, signature="deadbeef" * 8)
    # No webhook_events row written.
    res = await db_session.execute(
        select(WebhookEvent).where(WebhookEvent.event_id == "evt_badsig")
    )
    assert res.scalar_one_or_none() is None


# ── 2. Malformed payload ─────────────────────────────────────────────────────
async def test_malformed_payload_raises_400(db_session):
    body = b"not json at all"
    with pytest.raises(MalformedWebhookPayloadError):
        await _call(db_session, body)


async def test_missing_event_id_raises_400(db_session):
    body = json.dumps({"event": "subscription.activated", "payload": {}}).encode()
    with pytest.raises(MalformedWebhookPayloadError):
        await _call(db_session, body)


# ── 3. Happy-path grant ──────────────────────────────────────────────────────
async def test_activated_grants_plan_and_writes_audit(db_session):
    user = await _make_user(db_session)
    sub = await _make_sub(
        db_session, user, tier="pro", status="created", rzp_sub_id="sub_grant"
    )
    body = _event(
        "subscription.activated",
        event_id="evt_grant",
        subscription={"id": "sub_grant", "current_end": 1893456000},
    )
    result = await _call(db_session, body)
    assert result.event_type == "subscription.activated"

    await db_session.refresh(sub)
    await db_session.refresh(user)
    assert sub.status == "active"
    assert user.plan == "pro"
    assert sub.current_period_end is not None

    we = (
        await db_session.execute(
            select(WebhookEvent).where(WebhookEvent.event_id == "evt_grant")
        )
    ).scalar_one()
    assert we.processed_at is not None

    audits = (
        await db_session.execute(
            select(AuditEvent).where(AuditEvent.user_id == user.id)
        )
    ).scalars().all()
    assert any(a.event_type == "billing.plan.granted" for a in audits)


# ── 4. Idempotent replay (headline) ──────────────────────────────────────────
async def test_replay_is_idempotent(db_session):
    user = await _make_user(db_session)
    sub = await _make_sub(
        db_session, user, tier="pro", status="created", rzp_sub_id="sub_replay"
    )
    body = _event(
        "subscription.activated",
        event_id="evt_replay",
        subscription={"id": "sub_replay", "current_end": 1893456000},
    )
    await _call(db_session, body)
    # Second delivery of the SAME event_id.
    result2 = await _call(db_session, body)
    assert result2.audit_event_id is None  # dedupe no-op

    await db_session.refresh(sub)
    assert sub.status == "active"
    # Exactly one webhook_events row, exactly one grant audit row.
    we_rows = (
        await db_session.execute(
            select(WebhookEvent).where(WebhookEvent.event_id == "evt_replay")
        )
    ).scalars().all()
    assert len(we_rows) == 1
    grant_audits = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.user_id == user.id,
                AuditEvent.event_type == "billing.plan.granted",
            )
        )
    ).scalars().all()
    assert len(grant_audits) == 1


# ── 5. Atomic rollback ───────────────────────────────────────────────────────
async def test_handler_failure_rolls_back_dedupe_row(db_session, monkeypatch):
    """The dedupe INSERT + state mutation are ONE transaction (§4.2).

    Exercises the self-acquired-session path (``db=None``) which owns its own
    transaction boundary (the production route's ``get_db`` provides the same
    guarantee via commit/rollback-on-exception).  The ``db_session`` fixture
    rebinds ``iam.service.AsyncSessionLocal`` onto the test connection, so the
    self-acquired session shares the test transaction — after the handler raises
    and the ``async with`` unwinds, neither the dedupe row NOR the mutation is
    visible.
    """
    user = await _make_user(db_session)
    sub = await _make_sub(
        db_session, user, tier="pro", status="created", rzp_sub_id="sub_atomic"
    )
    await db_session.commit()  # land the seed onto the savepoint so db=None sees it
    body = _event(
        "subscription.activated",
        event_id="evt_atomic",
        subscription={"id": "sub_atomic", "current_end": 1893456000},
    )

    async def _boom(*a, **k):
        raise RuntimeError("handler blew up mid-processing")

    monkeypatch.setitem(
        iam_service._EVENT_HANDLERS, "subscription.activated", _boom
    )
    with pytest.raises(RuntimeError):
        # db=None → owns_transaction path; AsyncSessionLocal is rebound to the
        # test connection by the db_session fixture.
        await iam_service.capture_razorpay_webhook(body, _sign(body))

    # Dedupe row must be GONE (the whole transaction rolled back) so a Razorpay
    # retry reprocesses cleanly; sub status unchanged.
    res = await db_session.execute(
        select(WebhookEvent).where(WebhookEvent.event_id == "evt_atomic")
    )
    assert res.scalar_one_or_none() is None
    await db_session.refresh(sub)
    assert sub.status == "created"


# ── 6. Out-of-order period guard ─────────────────────────────────────────────
async def test_charged_period_is_monotonic(db_session):
    user = await _make_user(db_session, plan="pro")
    sub = await _make_sub(
        db_session, user, tier="pro", status="active", rzp_sub_id="sub_mono"
    )
    # Later charge first.
    await _call(
        db_session,
        _event(
            "subscription.charged",
            event_id="evt_late",
            subscription={"id": "sub_mono", "current_end": 2000000000},
            payment={"id": "pay_late", "amount": 49900, "currency": "INR"},
        ),
    )
    await db_session.refresh(sub)
    later = sub.current_period_end
    # Earlier charge arrives afterwards — must NOT rewind.
    await _call(
        db_session,
        _event(
            "subscription.charged",
            event_id="evt_early",
            subscription={"id": "sub_mono", "current_end": 1000000000},
            payment={"id": "pay_early", "amount": 49900, "currency": "INR"},
        ),
    )
    await db_session.refresh(sub)
    assert sub.current_period_end == later  # GREATEST guard


async def test_late_charge_does_not_reactivate_cancelled(db_session):
    user = await _make_user(db_session, plan="pro")
    sub = await _make_sub(
        db_session, user, tier="pro", status="cancelled", rzp_sub_id="sub_cxl"
    )
    await _call(
        db_session,
        _event(
            "subscription.charged",
            event_id="evt_latecharge",
            subscription={"id": "sub_cxl", "current_end": 2000000000},
            payment={"id": "pay_z", "amount": 49900},
        ),
    )
    await db_session.refresh(sub)
    assert sub.status == "cancelled"  # stays cancelled


# ── 7. LTD path ──────────────────────────────────────────────────────────────
async def test_ltd_payment_captured_grants_perpetual(db_session):
    user = await _make_user(db_session)
    sub = await _make_sub(
        db_session, user, tier="ltd", status="created", rzp_order_id="order_ltd"
    )
    body = _event(
        "payment.captured",
        event_id="evt_ltd",
        payment={"id": "pay_ltd", "amount": 499900, "order_id": "order_ltd"},
        order={"id": "order_ltd", "notes": {"tier": "ltd"}},
    )
    await _call(db_session, body)
    await db_session.refresh(sub)
    await db_session.refresh(user)
    assert user.plan == "ltd"
    assert sub.status == "active"
    assert sub.current_period_end is None  # perpetual sentinel
    pay = (
        await db_session.execute(
            select(Payment).where(Payment.razorpay_payment_id == "pay_ltd")
        )
    ).scalar_one()
    assert pay.status == "captured"
    # Replay idempotent.
    await _call(db_session, body)
    pays = (
        await db_session.execute(
            select(Payment).where(Payment.razorpay_payment_id == "pay_ltd")
        )
    ).scalars().all()
    assert len(pays) == 1


# ── 8. Renewal ───────────────────────────────────────────────────────────────
async def test_charged_renewal_writes_payment_keeps_active(db_session):
    user = await _make_user(db_session, plan="pro")
    sub = await _make_sub(
        db_session, user, tier="pro", status="active", rzp_sub_id="sub_renew"
    )
    await _call(
        db_session,
        _event(
            "subscription.charged",
            event_id="evt_renew",
            subscription={"id": "sub_renew", "current_end": 1893456000},
            payment={"id": "pay_renew", "amount": 49900, "currency": "INR"},
        ),
    )
    await db_session.refresh(sub)
    assert sub.status == "active"
    assert sub.current_period_end is not None
    pay = (
        await db_session.execute(
            select(Payment).where(Payment.razorpay_payment_id == "pay_renew")
        )
    ).scalar_one()
    assert pay.status == "captured"


# ── 9. Halt downgrade ────────────────────────────────────────────────────────
async def test_halted_downgrades_to_free(db_session):
    user = await _make_user(db_session, plan="pro")
    sub = await _make_sub(
        db_session, user, tier="pro", status="active", rzp_sub_id="sub_halt"
    )
    await _call(
        db_session,
        _event(
            "subscription.halted",
            event_id="evt_halt",
            subscription={"id": "sub_halt"},
        ),
    )
    await db_session.refresh(sub)
    await db_session.refresh(user)
    assert sub.status == "halted"
    assert user.plan == "free"  # F8


# ── 10. Unknown event type ───────────────────────────────────────────────────
async def test_unknown_event_recorded_no_dispatch(db_session):
    user = await _make_user(db_session, plan="pro")
    sub = await _make_sub(
        db_session, user, tier="pro", status="active", rzp_sub_id="sub_unknown"
    )
    body = _event(
        "subscription.some_future_event",
        event_id="evt_unknown",
        subscription={"id": "sub_unknown"},
    )
    result = await _call(db_session, body)
    assert result.audit_event_id is None
    we = (
        await db_session.execute(
            select(WebhookEvent).where(WebhookEvent.event_id == "evt_unknown")
        )
    ).scalar_one()
    assert we.processed_at is not None  # recorded + marked processed
    await db_session.refresh(sub)
    assert sub.status == "active"  # no state change


# ── 11. Cancelled handler keeps tier until period end ────────────────────────
async def test_cancelled_sets_status_keeps_plan(db_session):
    user = await _make_user(db_session, plan="pro")
    sub = await _make_sub(
        db_session, user, tier="pro", status="active", rzp_sub_id="sub_cancel"
    )
    await _call(
        db_session,
        _event(
            "subscription.cancelled",
            event_id="evt_cancel",
            subscription={"id": "sub_cancel"},
        ),
    )
    await db_session.refresh(sub)
    await db_session.refresh(user)
    assert sub.status == "cancelled"
    assert user.plan == "pro"  # entitlement persists until current_period_end


# ── QA Wave 1 — P0.5: tampered-signature i18n guard ──────────────────────────
async def test_tampered_signature_has_non_empty_validation_message_id(db_session):
    """Pair for test_bad_signature_raises_401_and_no_state_change.

    The existing test confirms the EXCEPTION type is raised.  This test
    asserts the route-level response for a tampered payload: the 401 response
    envelope must carry a non-empty ``validation_message_id`` so the frontend
    can surface a human-readable message (P0 item 14 blank-error guard).

    This exercises the HTTP-level response via the FastAPI error handler,
    not the service directly.
    """
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    body = _event(
        "subscription.activated",
        event_id="evt_tampered_i18n",
        subscription={"id": "sub_tampered_i18n"},
    )
    tampered_sig = "00" * 32  # 64 hex chars — valid length, wrong HMAC

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        resp = await ac.post(
            "/api/v1/webhooks/razorpay",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": tampered_sig,
            },
        )

    assert resp.status_code == 401, (
        f"Tampered sig expected 401, got {resp.status_code}: {resp.text}"
    )
    resp_body = resp.json()
    # P0 item 14: validation_message_id must be a non-empty string.
    msg_id = resp_body.get("validation_message_id", "")
    assert isinstance(msg_id, str) and msg_id, (
        f"401 tampered-sig must carry non-empty validation_message_id; got {resp_body!r}"
    )
