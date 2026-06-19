"""Billing service-layer tests — Razorpay Wave 3 (auth-builder, step 2a).

Covers the entitlement-shaped service helpers authored by the auth-builder:
``iam.service.start_trial`` (§3.7 app-side trial) + ``iam.service.get_billing_status``
(the DB-fresh read backing ``/auth/me`` + ``GET /billing/subscription``), and the
DB-fresh ``core.plan_guard.resolve_entitlement`` against a REAL Postgres row
(the F7 proof — entitlement is read from the DB, not the JWT).

All tests are integration tests using the rolled-back ``db`` AsyncSession
(mirrors ``tests/test_billing_models.py`` — zero data leaks; the outer
transaction is rolled back at teardown).

pytestmark: integration (requires a *_test Postgres via TEST_DATABASE_URL).

🛑 DB-ISOLATION: this file NEVER targets the dev ``meesell`` DB.  The ``db``
fixture resolves ``TEST_DATABASE_URL`` (a disposable ``*_test`` DB) and the
top-level conftest guard refuses any DB whose name does not end in ``_test``.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.plan_guard import resolve_entitlement
from app.modules.iam import service as iam_service
from app.modules.iam.exceptions import TrialAlreadyUsedError
from app.shared.models import Subscription, User

pytestmark = pytest.mark.integration


_DEV_DATABASE_URL = (
    os.environ.get("TEST_DATABASE_URL")
    or os.environ.get("DEV_DATABASE_URL")
    or "postgresql+asyncpg://meesell:j3w%2F6o%2F7k%2FJwjPu1J4OqDpFStho7IsK%2F0lRYnwmbN6Q%3D@localhost:5433/meesell"
)


@pytest_asyncio.fixture(loop_scope="function")
async def db() -> AsyncSession:
    """Rolled-back AsyncSession per test.  Zero data leaks to Postgres."""
    eng = create_async_engine(_DEV_DATABASE_URL, poolclass=NullPool, echo=False)
    try:
        async with eng.connect() as conn:
            await conn.begin()
            Session = async_sessionmaker(
                bind=conn, expire_on_commit=False, class_=AsyncSession
            )
            session = Session()
            try:
                yield session
            finally:
                await session.close()
                await conn.rollback()
    finally:
        await eng.dispose()


async def _create_user(
    db: AsyncSession,
    *,
    plan: str = "free",
    trial_ends_at: datetime | None = None,
) -> User:
    user = User(
        phone=f"+9155500{uuid.uuid4().int % 100000:05d}",
        plan=plan,
        trial_ends_at=trial_ends_at,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_sub(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    tier: str = "pro",
    status: str = "active",
    current_period_end: datetime | None = None,
    cancel_scheduled_at: datetime | None = None,
) -> Subscription:
    sub = Subscription(
        user_id=user_id,
        tier=tier,
        status=status,
        current_period_end=current_period_end,
        cancel_scheduled_at=cancel_scheduled_at,
        razorpay_subscription_id=f"sub_{uuid.uuid4().hex[:18]}",
    )
    db.add(sub)
    await db.flush()
    return sub


# ─────────────────────────────────────────────────────────────────────────────
# start_trial — §8.5 / §8.6 (app-side, idempotent one-per-phone)
# ─────────────────────────────────────────────────────────────────────────────
class TestStartTrial:
    async def test_start_trial_first_time_grants_14_days(self, db: AsyncSession):
        user = await _create_user(db)
        before = datetime.now(timezone.utc)
        result = await iam_service.start_trial(user.id, db)
        # ~14 days out (allow a small execution-time window).
        delta = result.trial_ends_at - before
        assert timedelta(days=13, hours=23) < delta < timedelta(days=14, minutes=5)
        assert result.entitlement == "pro"
        # The users row was mutated.
        await db.refresh(user)
        assert user.trial_ends_at is not None
        # NO subscriptions row was created (app-side only).
        from sqlalchemy import func, select

        cnt = (
            await db.execute(
                select(func.count(Subscription.id)).where(
                    Subscription.user_id == user.id
                )
            )
        ).scalar_one()
        assert cnt == 0

    async def test_start_trial_second_time_rejected_409(self, db: AsyncSession):
        """Idempotent: a user who already has trial_ends_at cannot re-trial."""
        user = await _create_user(
            db, trial_ends_at=datetime.now(timezone.utc) + timedelta(days=3)
        )
        with pytest.raises(TrialAlreadyUsedError) as exc:
            await iam_service.start_trial(user.id, db)
        assert exc.value.status_code == 409

    async def test_start_trial_expired_trial_still_rejected(self, db: AsyncSession):
        """One-per-phone is permanent — an EXPIRED trial still blocks a re-grant."""
        user = await _create_user(
            db, trial_ends_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        with pytest.raises(TrialAlreadyUsedError):
            await iam_service.start_trial(user.id, db)

    async def test_start_trial_paid_plan_rejected(self, db: AsyncSession):
        user = await _create_user(db, plan="pro")
        with pytest.raises(TrialAlreadyUsedError):
            await iam_service.start_trial(user.id, db)


# ─────────────────────────────────────────────────────────────────────────────
# get_billing_status — §8.9 (free / trial / active-pro / ltd / cancelled)
# ─────────────────────────────────────────────────────────────────────────────
class TestGetBillingStatus:
    async def test_free_user(self, db: AsyncSession):
        user = await _create_user(db)
        status = await iam_service.get_billing_status(user.id, db)
        assert status.plan == "free"
        assert status.entitlement == "free"
        assert status.status is None
        assert status.trial_ends_at is None
        assert status.tier_label == "Free"
        assert status.cancel_scheduled is False

    async def test_trialist_plan_free_entitlement_pro(self, db: AsyncSession):
        """F7 proof: plan stays 'free' but entitlement resolves to 'pro'."""
        user = await _create_user(
            db, trial_ends_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        status = await iam_service.get_billing_status(user.id, db)
        assert status.plan == "free"
        assert status.entitlement == "pro"
        assert status.trial_ends_at is not None

    async def test_active_pro(self, db: AsyncSession):
        user = await _create_user(db, plan="pro")
        await _create_sub(db, user.id, tier="pro", status="active")
        status = await iam_service.get_billing_status(user.id, db)
        assert status.plan == "pro"
        assert status.entitlement == "pro"
        assert status.status == "active"
        assert status.tier_label == "Pro"

    async def test_ltd_perpetual(self, db: AsyncSession):
        user = await _create_user(db, plan="ltd")
        await _create_sub(
            db, user.id, tier="ltd", status="active", current_period_end=None
        )
        status = await iam_service.get_billing_status(user.id, db)
        assert status.plan == "ltd"
        assert status.entitlement == "pro"
        assert status.current_period_end is None
        assert status.tier_label == "Lifetime"

    async def test_annual_collapses_to_base(self, db: AsyncSession):
        user = await _create_user(db, plan="business_annual")
        await _create_sub(db, user.id, tier="business_annual", status="active")
        status = await iam_service.get_billing_status(user.id, db)
        assert status.plan == "business_annual"
        assert status.entitlement == "business"
        assert status.tier_label == "Business (Annual)"

    async def test_cancelled_before_period_end(self, db: AsyncSession):
        user = await _create_user(db, plan="pro")
        await _create_sub(
            db,
            user.id,
            tier="pro",
            status="cancelled",
            current_period_end=datetime.now(timezone.utc) + timedelta(days=4),
            cancel_scheduled_at=datetime.now(timezone.utc),
        )
        status = await iam_service.get_billing_status(user.id, db)
        # Still entitled (paid through the period); cancel scheduled flag set.
        assert status.entitlement == "pro"
        assert status.cancel_scheduled is True


# ─────────────────────────────────────────────────────────────────────────────
# resolve_entitlement against a REAL row (the DB-fresh F7 proof)
# ─────────────────────────────────────────────────────────────────────────────
class TestResolveEntitlementDb:
    async def test_starter_active_db_fresh(self, db: AsyncSession):
        user = await _create_user(db, plan="starter")
        await _create_sub(db, user.id, tier="starter", status="active")
        assert await resolve_entitlement(user_id=user.id, db=db) == "starter"

    async def test_paid_plan_halted_sub_falls_back_free(self, db: AsyncSession):
        user = await _create_user(db, plan="pro")
        await _create_sub(db, user.id, tier="pro", status="halted")
        assert await resolve_entitlement(user_id=user.id, db=db) == "free"

    async def test_free_expired_trial_db_fresh(self, db: AsyncSession):
        user = await _create_user(
            db, trial_ends_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        assert await resolve_entitlement(user_id=user.id, db=db) == "free"
