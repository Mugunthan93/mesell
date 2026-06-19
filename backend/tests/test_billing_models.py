"""Billing models tests — Razorpay Wave 1.

Covers RAZORPAY_INTEGRATION_SPEC §9 items 1–7 (items 1–7 automated here;
item 8 migration round-trip is documented via manual CLI evidence in the PR).

All tests are integration tests — they use the real Postgres dev tunnel via the
``db`` fixture (rolled-back AsyncSession per test per conftest §19.D posture).

pytestmark: integration (requires dev Postgres via SSH tunnel / TEST_DATABASE_URL)
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.shared.models import (
    Payment,
    Subscription,
    User,
    WebhookEvent,
)

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# DEV DB URL resolution — mirrors conftest._DEV_DATABASE_URL pattern
# ---------------------------------------------------------------------------

_DEV_DATABASE_URL = (
    os.environ.get("TEST_DATABASE_URL")
    or os.environ.get("DEV_DATABASE_URL")
    or "postgresql+asyncpg://meesell:j3w%2F6o%2F7k%2FJwjPu1J4OqDpFStho7IsK%2F0lRYnwmbN6Q%3D@localhost:5433/meesell"
)


# ---------------------------------------------------------------------------
# db fixture (function-scoped, NullPool — per §19.D / Phase 4 canonical pattern)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(loop_scope="function")
async def db() -> AsyncSession:
    """Rolled-back AsyncSession per test.  Zero data leaks to dev Postgres."""
    eng = create_async_engine(_DEV_DATABASE_URL, poolclass=NullPool, echo=False)
    try:
        async with eng.connect() as conn:
            await conn.begin()
            Session = async_sessionmaker(bind=conn, expire_on_commit=False, class_=AsyncSession)
            session = Session()
            try:
                yield session
            finally:
                await session.close()
                await conn.rollback()
    finally:
        await eng.dispose()


# ---------------------------------------------------------------------------
# Helpers — create seed data within the rolled-back transaction
# ---------------------------------------------------------------------------

async def _create_user(session: AsyncSession, *, phone: str | None = None) -> User:
    """Insert a User row with a unique phone number."""
    if phone is None:
        phone = f"+9199{uuid.uuid4().int % 100000000:08d}"
    user = User(phone=phone)
    session.add(user)
    await session.flush()
    return user


async def _create_subscription(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    tier: str = "pro",
    status: str = "active",
    razorpay_subscription_id: str | None = None,
    razorpay_order_id: str | None = None,
) -> Subscription:
    sub = Subscription(
        user_id=user_id,
        tier=tier,
        status=status,
        razorpay_subscription_id=razorpay_subscription_id,
        razorpay_order_id=razorpay_order_id,
    )
    session.add(sub)
    await session.flush()
    return sub


# ===========================================================================
# §9 Item 1 — CRUD instantiation + server defaults
# ===========================================================================

class TestCRUDInstantiation:
    """Insert + read-back one row per new table; verify server defaults."""

    async def test_subscription_insert_and_readback(self, db: AsyncSession) -> None:
        """Subscription row: id + created_at + updated_at are server-defaults."""
        user = await _create_user(db)
        sub = await _create_subscription(db, user.id)

        assert sub.id is not None
        assert isinstance(sub.id, uuid.UUID)
        assert sub.tier == "pro"
        assert sub.status == "active"
        assert sub.created_at is not None
        assert sub.updated_at is not None
        assert sub.current_period_end is None  # LTD-sentinel NULL is default

    async def test_payment_insert_and_readback(self, db: AsyncSession) -> None:
        """Payment row: id + created_at server defaults; currency defaults to INR."""
        user = await _create_user(db)
        sub = await _create_subscription(db, user.id)
        payment = Payment(
            user_id=user.id,
            subscription_id=sub.id,
            amount_paise=49900,
            status="captured",
        )
        db.add(payment)
        await db.flush()

        assert payment.id is not None
        assert payment.currency == "INR"
        assert payment.created_at is not None
        assert payment.amount_paise == 49900

    async def test_webhook_event_insert_and_readback(self, db: AsyncSession) -> None:
        """WebhookEvent row: received_at is server-default; string PK is preserved."""
        event_id = f"evt_{uuid.uuid4().hex}"
        we = WebhookEvent(
            event_id=event_id,
            event_type="subscription.charged",
            payload_jsonb={"id": event_id, "entity": "event"},
            signature_valid=True,
        )
        db.add(we)
        await db.flush()

        assert we.event_id == event_id
        assert we.received_at is not None
        assert we.processed_at is None
        assert we.processing_error is None


# ===========================================================================
# §9 Item 2 — FK enforcement
# ===========================================================================

class TestFKEnforcement:
    """FK constraint violations raise IntegrityError."""

    async def test_subscription_nonexistent_user_raises(self, db: AsyncSession) -> None:
        """Inserting a subscription with a nonexistent user_id raises IntegrityError."""
        sub = Subscription(
            user_id=uuid.uuid4(),  # does not exist
            tier="pro",
            status="active",
        )
        db.add(sub)
        with pytest.raises(IntegrityError):
            await db.flush()

    async def test_payment_nonexistent_user_raises(self, db: AsyncSession) -> None:
        """Inserting a payment with a nonexistent user_id raises IntegrityError."""
        payment = Payment(
            user_id=uuid.uuid4(),  # does not exist
            amount_paise=49900,
            status="captured",
        )
        db.add(payment)
        with pytest.raises(IntegrityError):
            await db.flush()

    async def test_payment_null_subscription_id_succeeds(self, db: AsyncSession) -> None:
        """payment.subscription_id accepts NULL — valid for LTD order payments."""
        user = await _create_user(db)
        payment = Payment(
            user_id=user.id,
            subscription_id=None,  # explicitly NULL
            amount_paise=499900,  # ₹4,999 LTD
            status="captured",
        )
        db.add(payment)
        await db.flush()
        assert payment.subscription_id is None
        assert payment.id is not None


# ===========================================================================
# §9 Item 3 — CHECK constraint enforcement
# ===========================================================================

class TestCheckConstraints:
    """CHECK constraint violations raise IntegrityError."""

    async def test_subscription_tier_free_raises(self, db: AsyncSession) -> None:
        """subscriptions.tier='free' raises — free is NOT a subscription tier."""
        user = await _create_user(db)
        sub = Subscription(user_id=user.id, tier="free", status="active")
        db.add(sub)
        with pytest.raises(IntegrityError, match="ck_subscriptions_tier"):
            await db.flush()

    async def test_subscription_status_bogus_raises(self, db: AsyncSession) -> None:
        """subscriptions.status='bogus' raises — not in the allowed status set."""
        user = await _create_user(db)
        sub = Subscription(user_id=user.id, tier="pro", status="bogus")
        db.add(sub)
        with pytest.raises(IntegrityError, match="ck_subscriptions_status"):
            await db.flush()

    async def test_payment_status_bogus_raises(self, db: AsyncSession) -> None:
        """payments.status='bogus' raises — not in allowed payment status set."""
        user = await _create_user(db)
        payment = Payment(user_id=user.id, amount_paise=100, status="bogus")
        db.add(payment)
        with pytest.raises(IntegrityError, match="ck_payments_status"):
            await db.flush()

    async def test_users_plan_bogus_raises(self, db: AsyncSession) -> None:
        """users.plan='bogus' raises — ck_users_plan CHECK added in Wave 1."""
        user = await _create_user(db)
        user.plan = "bogus"
        db.add(user)
        with pytest.raises(IntegrityError, match="ck_users_plan"):
            await db.flush()

    async def test_users_plan_starter_succeeds(self, db: AsyncSession) -> None:
        """users.plan='starter' succeeds — 'starter' is now in the allowed plan set."""
        user = await _create_user(db)
        user.plan = "starter"
        db.add(user)
        await db.flush()
        assert user.plan == "starter"


# ===========================================================================
# §9 Item 4 — UNIQUE constraint enforcement + NULL-multiplicity
# ===========================================================================

class TestUniqueConstraints:
    """UNIQUE constraints raise IntegrityError on duplicates; NULLs are allowed multiple times."""

    async def test_duplicate_razorpay_subscription_id_raises(self, db: AsyncSession) -> None:
        """Two subscriptions with the same non-NULL razorpay_subscription_id raise."""
        user = await _create_user(db)
        sub_id = f"sub_{uuid.uuid4().hex[:16]}"
        await _create_subscription(db, user.id, razorpay_subscription_id=sub_id)
        sub2 = Subscription(
            user_id=user.id,
            tier="starter",
            status="cancelled",
            razorpay_subscription_id=sub_id,  # duplicate
        )
        db.add(sub2)
        with pytest.raises(IntegrityError, match="uq_subscriptions_razorpay_sub_id"):
            await db.flush()

    async def test_multiple_null_razorpay_subscription_id_succeeds(self, db: AsyncSession) -> None:
        """Two subscriptions with NULL razorpay_subscription_id both succeed (LTD path)."""
        user = await _create_user(db)
        # Two LTD-style rows, both with NULL razorpay_subscription_id
        s1 = Subscription(
            user_id=user.id,
            tier="ltd",
            status="active",
            razorpay_subscription_id=None,
            razorpay_order_id=f"order_{uuid.uuid4().hex[:12]}",
        )
        s2 = Subscription(
            user_id=user.id,
            tier="ltd",
            status="cancelled",
            razorpay_subscription_id=None,  # also NULL — allowed
            razorpay_order_id=f"order_{uuid.uuid4().hex[:12]}",
        )
        db.add_all([s1, s2])
        await db.flush()  # must not raise
        assert s1.id is not None
        assert s2.id is not None

    async def test_duplicate_webhook_event_id_raises(self, db: AsyncSession) -> None:
        """Two WebhookEvent rows with the same event_id raise — the dedupe key sanity."""
        event_id = f"evt_{uuid.uuid4().hex}"
        we1 = WebhookEvent(
            event_id=event_id,
            event_type="subscription.charged",
            payload_jsonb={"id": event_id},
            signature_valid=True,
        )
        we2 = WebhookEvent(
            event_id=event_id,  # duplicate PK
            event_type="subscription.charged",
            payload_jsonb={"id": event_id, "duplicate": True},
            signature_valid=True,
        )
        db.add(we1)
        await db.flush()
        db.add(we2)
        with pytest.raises(IntegrityError):
            await db.flush()


# ===========================================================================
# §9 Item 5 — Partial unique "one active sub per user"
# ===========================================================================

class TestPartialUniqueActiveSubscription:
    """uq_subscriptions_one_active_per_user prevents two active subs for one user."""

    async def test_two_active_subs_same_user_raises(self, db: AsyncSession) -> None:
        """A user cannot have two subscriptions with status='active' simultaneously."""
        user = await _create_user(db)
        await _create_subscription(db, user.id, status="active", tier="pro")
        sub2 = Subscription(user_id=user.id, tier="starter", status="active")
        db.add(sub2)
        with pytest.raises(IntegrityError, match="uq_subscriptions_one_active_per_user"):
            await db.flush()

    async def test_one_active_one_cancelled_same_user_succeeds(self, db: AsyncSession) -> None:
        """An active + a cancelled subscription for the same user is valid."""
        user = await _create_user(db)
        await _create_subscription(db, user.id, status="active", tier="pro")
        # cancelled does not participate in the partial UNIQUE (only active rows)
        sub2 = Subscription(user_id=user.id, tier="pro", status="cancelled")
        db.add(sub2)
        await db.flush()  # must not raise
        assert sub2.id is not None


# ===========================================================================
# §9 Item 6 — JSONB round-trip
# ===========================================================================

class TestJsonbRoundTrip:
    """JSONB columns preserve nested dicts unchanged on write + read."""

    async def test_webhook_event_payload_jsonb_roundtrip(self, db: AsyncSession) -> None:
        """webhook_events.payload_jsonb: nested dict written + read-back unchanged."""
        payload = {
            "id": f"evt_{uuid.uuid4().hex}",
            "entity": "event",
            "event": "subscription.charged",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": f"pay_{uuid.uuid4().hex}",
                        "amount": 49900,
                    }
                }
            },
        }
        event_id = payload["id"]
        we = WebhookEvent(
            event_id=event_id,
            event_type="subscription.charged",
            payload_jsonb=payload,
            signature_valid=True,
        )
        db.add(we)
        await db.flush()
        await db.refresh(we)
        assert we.payload_jsonb == payload
        assert we.payload_jsonb["payload"]["payment"]["entity"]["amount"] == 49900

    async def test_payment_raw_jsonb_roundtrip(self, db: AsyncSession) -> None:
        """payments.raw_jsonb: nested dict written + read-back unchanged."""
        user = await _create_user(db)
        raw = {
            "subscription_id": f"sub_{uuid.uuid4().hex[:16]}",
            "charge_at": "1718000000",
            "total_count": 12,
            "paid_count": 1,
            "metadata": {"catalog_session": "abc123"},
        }
        payment = Payment(
            user_id=user.id,
            amount_paise=49900,
            status="captured",
            raw_jsonb=raw,
        )
        db.add(payment)
        await db.flush()
        await db.refresh(payment)
        assert payment.raw_jsonb == raw
        assert payment.raw_jsonb["metadata"]["catalog_session"] == "abc123"


# ===========================================================================
# §9 Item 7 — users.trial_ends_at
# ===========================================================================

class TestTrialEndsAt:
    """users.trial_ends_at: set + read-back; NULL default verified."""

    async def test_trial_ends_at_null_by_default(self, db: AsyncSession) -> None:
        """A freshly created user has trial_ends_at = NULL."""
        user = await _create_user(db)
        await db.refresh(user)
        assert user.trial_ends_at is None

    async def test_trial_ends_at_set_and_readback(self, db: AsyncSession) -> None:
        """Setting trial_ends_at and reading it back returns the same timestamp."""
        user = await _create_user(db)
        trial_end = datetime(2026, 7, 3, 12, 0, 0, tzinfo=timezone.utc)
        user.trial_ends_at = trial_end
        db.add(user)
        await db.flush()
        await db.refresh(user)
        # Compare as UTC-aware timestamps (DB returns UTC)
        assert user.trial_ends_at is not None
        assert user.trial_ends_at.replace(tzinfo=timezone.utc) == trial_end
