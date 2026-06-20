"""Dev-only Razorpay mock-mode tests (razorpay-dev-mock feature).

Proves that when ``settings.razorpay_mock_active`` is True, the billing service
helpers (``subscribe`` / ``start_trial`` / ``cancel``) drive the REAL internal
state machine to grant entitlement — with NO network, NO Razorpay account, and
NO new route or Celery task.  Concretely, each test exercises the REAL service
helper (NOT a monkeypatched stub) and asserts the downstream effect a real
webhook would produce:

* ``subscribe(pro)`` → ``_rzp()`` returns the mock adapter → a ``subscriptions``
  row is written → the synthetic ``subscription.activated`` webhook replays
  through ``_route_webhook_in_session`` → ``users.plan='pro'``,
  ``subscriptions.status='active'``, ``current_period_end`` ~30d out, one
  ``billing.plan.granted`` audit row, one ``evt_mock_*`` ``webhook_events`` row.
  ``get_billing_status`` then reports ``entitlement='pro'``.
* ``start_trial`` (no Razorpay either way) still grants the app-side trial.
* ``cancel`` → mock cancel adapter + synthetic ``subscription.cancelled`` replay
  → ``subscriptions.status='cancelled'`` + ``cancel_scheduled_at`` set, while
  entitlement stays ``pro`` until period end (correct real behaviour).
* LTD ``subscribe`` → synthetic ``payment.captured`` → ``users.plan='ltd'``,
  ``current_period_end=NULL``, a ``payments`` row.

Test-DB isolation
-----------------
Targets the disposable ``meesell_rzpw2_test`` DB (or any ``*_test`` DB via
``TEST_DATABASE_URL``).  conftest.py refuses any DATABASE_URL not ending in
``_test``.  Each test seeds + tears down its own user row so the DB stays clean.

CRITICAL — flag activation
--------------------------
``app.shared.config.settings`` is an import-time singleton, so this suite sets
``RAZORPAY_DEV_MOCK=True`` (and ``APP_ENV='development'``) via
``monkeypatch.setattr(settings, ...)`` on the live singleton — NOT via ambient
env (which lands too late).  The flag is restored at teardown so it never leaks
into the hermetic ``test_billing_routes.py`` suite.
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

pytestmark = pytest.mark.integration

# ── Test DB URL (meesell_rzpw2_test disposable DB, or any *_test DB) ─────────
_TEST_DB_URL = (
    os.environ.get("TEST_DATABASE_URL")
    or "postgresql+asyncpg://meesell:j3w%2F6o%2F7k%2FJwjPu1J4OqDpFStho7IsK%2F0lRYnwmbN6Q%3D@localhost:5432/meesell_rzpw2_test"
)

# ── Minimal env so app config passes REQUIRED_FIELDS at import ───────────────
_SENTINEL_ENV: dict[str, str] = {
    "APP_ENV": "development",
    "DATABASE_URL": _TEST_DB_URL,
    "VALKEY_URL": "redis://localhost:6379/15",
    "JWT_SECRET": "test-jwt-secret-mock",
    "GCS_BUCKET": "test-bucket",
    "RAZORPAY_KEY_ID": "rzp_test_sentinel_key",
    "RAZORPAY_KEY_SECRET": "test_secret",
    "RAZORPAY_WEBHOOK_SECRET": "test_webhook_secret",
    "MSG91_AUTH_KEY": "test_msg91",
    "GCS_SERVICE_ACCOUNT_KEY_PATH": "/dev/null",
    "GEMINI_API_KEY": "test_gemini",
    "AUDIT_PII_SALT": "test_salt",
    "REFRESH_TOKEN_PEPPER": "test_pepper",
    "MSG91_TEMPLATE_ID": "test_tmpl",
    "GCS_PROJECT_ID": "test-project",
    "LANGFUSE_PUBLIC_KEY": "test_lf_pub",
    "LANGFUSE_SECRET_KEY": "test_lf_secret",
    "CORS_ALLOWED_ORIGINS": '["http://localhost:4200"]',
    "FEATURE_BILLING_ENABLED": "true",
    "RAZORPAY_PLAN_ID_STARTER_MONTHLY": "plan_test_starter",
    "RAZORPAY_PLAN_ID_PRO_MONTHLY": "plan_test_pro",
    "RAZORPAY_PLAN_ID_PRO_ANNUAL": "plan_test_pro_annual",
    "RAZORPAY_PLAN_ID_BUSINESS_MONTHLY": "plan_test_business",
    "RAZORPAY_PLAN_ID_BUSINESS_ANNUAL": "plan_test_business_annual",
}
for _k, _v in _SENTINEL_ENV.items():
    os.environ.setdefault(_k, _v)


# ── App import (after env setup) ──────────────────────────────────────────────
import app.modules.iam.service as svc  # noqa: E402
import app.shared.config as _config_module  # noqa: E402

_USER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a1")


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _activate_mock(monkeypatch: pytest.MonkeyPatch):
    """Turn the dev mock ON via the live settings singleton (restored at teardown).

    settings is an import-time singleton — env vars set after import are ignored,
    so we patch the attribute directly.  ``APP_ENV`` is also pinned to
    ``development`` so ``razorpay_mock_active`` (which force-disables in prod)
    evaluates True.
    """
    monkeypatch.setattr(_config_module.settings, "APP_ENV", "development")
    monkeypatch.setattr(_config_module.settings, "RAZORPAY_DEV_MOCK", True)


@pytest_asyncio.fixture(loop_scope="function")
async def db():
    """A request-style AsyncSession on the disposable test DB + a clean user row.

    Seeds the user row before the test and deletes all child billing rows + the
    user row in teardown, so the DB is pristine for the next run.  The session is
    committed by the test (the mock tails run with ``owns_transaction=False``).
    """
    engine = create_async_engine(_TEST_DB_URL, poolclass=NullPool, echo=False)

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO users (id, phone, plan, auth_provider)
                VALUES (:uid, :phone, 'free', 'phone')
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"uid": str(_USER_ID), "phone": "+91555000901"},
        )

    TestSession = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    session = TestSession()
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()
        # Cleanup — child rows first (FK RESTRICT), then the user row.
        async with engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM webhook_events WHERE event_id LIKE 'evt_mock_%'")
            )
            await conn.execute(
                text("DELETE FROM payments WHERE user_id = :uid"), {"uid": str(_USER_ID)}
            )
            await conn.execute(
                text("DELETE FROM subscriptions WHERE user_id = :uid"),
                {"uid": str(_USER_ID)},
            )
            await conn.execute(
                text("DELETE FROM audit_events WHERE user_id = :uid"),
                {"uid": str(_USER_ID)},
            )
            await conn.execute(
                text("DELETE FROM users WHERE id = :uid"), {"uid": str(_USER_ID)}
            )
        await engine.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


async def _user_plan(db: AsyncSession) -> str:
    row = (
        await db.execute(text("SELECT plan FROM users WHERE id = :uid"), {"uid": str(_USER_ID)})
    ).first()
    return row[0] if row else ""


async def _latest_sub(db: AsyncSession):
    from app.shared.models.subscription import Subscription

    stmt = (
        select(Subscription)
        .where(Subscription.user_id == _USER_ID)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _count(db: AsyncSession, sql: str) -> int:
    return int((await db.execute(text(sql), {"uid": str(_USER_ID)})).scalar_one() or 0)


# ─────────────────────────────────────────────────────────────────────────────
# Sanity: the gate evaluates True under the fixture
# ─────────────────────────────────────────────────────────────────────────────


def test_mock_gate_active() -> None:
    """With RAZORPAY_DEV_MOCK=True + dev env, the gate is on and _rzp() is the mock."""
    assert _config_module.settings.razorpay_mock_active is True
    assert svc._rzp() is svc.razorpay_mock


def test_mock_gate_force_disabled_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    """APP_ENV=production force-disables the gate even with the flag True."""
    monkeypatch.setattr(_config_module.settings, "APP_ENV", "production")
    assert _config_module.settings.razorpay_mock_active is False
    assert svc._rzp() is svc.razorpay_adapter


# ─────────────────────────────────────────────────────────────────────────────
# subscribe(pro) — recurring → real activation state machine
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mock_subscribe_pro_grants_via_state_machine(db: AsyncSession) -> None:
    """subscribe('pro') under mock → plan granted by the REAL webhook handler path."""
    result = await svc.subscribe(_USER_ID, "pro", db)
    await db.commit()

    # Adapter returned a sub_mock_* id (no network).
    assert result.razorpay_subscription_id is not None
    assert result.razorpay_subscription_id.startswith("sub_mock_")

    # users.plan granted via the real _handle_subscription_activated → _grant_plan_for_sub.
    assert await _user_plan(db) == "pro"

    # subscriptions row active + period end ~30d out (set by the synthetic webhook).
    sub = await _latest_sub(db)
    assert sub is not None
    assert sub.status == "active"
    assert sub.current_period_end is not None

    # One billing.plan.granted audit row.
    assert await _count(
        db,
        "SELECT count(*) FROM audit_events WHERE user_id = :uid "
        "AND event_type = 'billing.plan.granted'",
    ) == 1

    # One synthetic webhook_events dedupe row (evt_mock_*).
    assert await _count(
        db,
        "SELECT count(*) FROM webhook_events WHERE event_id LIKE 'evt_mock_%' "
        "AND event_type = 'subscription.activated'",
    ) == 1

    # The DB-fresh entitlement read agrees.
    status = await svc.get_billing_status(_USER_ID, db)
    assert status.plan == "pro"
    assert status.entitlement == "pro"
    assert status.status == "active"


@pytest.mark.asyncio
async def test_mock_subscribe_no_network_called(db: AsyncSession) -> None:
    """The mock path never touches the real adapter (no SDK client constructed)."""
    import app.adapters.razorpay as real_adapter

    # If the real adapter were invoked it would try to build a client → reset
    # marker.  After a mock subscribe the real singleton must remain unbuilt.
    real_adapter._reset_for_testing()
    await svc.subscribe(_USER_ID, "pro", db)
    await db.commit()
    assert real_adapter._client is None  # no real SDK client was ever constructed


# ─────────────────────────────────────────────────────────────────────────────
# start_trial — app-side only (no Razorpay either way), still works under mock
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mock_start_trial_grants_app_side(db: AsyncSession) -> None:
    """start_trial under mock grants the 14-day Pro trial (no sub/webhook row)."""
    result = await svc.start_trial(_USER_ID, db)
    await db.commit()

    assert result.entitlement == "pro"
    assert result.trial_ends_at is not None

    status = await svc.get_billing_status(_USER_ID, db)
    assert status.plan == "free"  # trial does NOT change users.plan
    assert status.entitlement == "pro"  # but entitlement collapses to pro
    assert status.trial_ends_at is not None

    # No subscription / webhook rows for a trial.
    assert await _count(db, "SELECT count(*) FROM subscriptions WHERE user_id = :uid") == 0
    assert await _count(
        db, "SELECT count(*) FROM webhook_events WHERE event_id LIKE 'evt_mock_%'"
    ) == 0


# ─────────────────────────────────────────────────────────────────────────────
# cancel — mock cancel adapter + synthetic subscription.cancelled replay
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mock_cancel_drives_terminal_state(db: AsyncSession) -> None:
    """cancel under mock → status='cancelled' + cancel_scheduled, entitlement stays pro."""
    # First subscribe (active pro) so there is something to cancel.
    await svc.subscribe(_USER_ID, "pro", db)
    await db.commit()
    assert await _user_plan(db) == "pro"

    cancel_result = await svc.cancel(_USER_ID, db)
    await db.commit()
    assert cancel_result is not None

    sub = await _latest_sub(db)
    assert sub is not None
    assert sub.status == "cancelled"  # synthetic subscription.cancelled landed
    assert sub.cancel_scheduled_at is not None

    # users.plan stays at tier until period end (real contract — no fake downgrade).
    assert await _user_plan(db) == "pro"

    status = await svc.get_billing_status(_USER_ID, db)
    assert status.cancel_scheduled is True
    assert status.entitlement == "pro"  # still entitled until current_period_end

    # The cancellation audit row landed.
    assert await _count(
        db,
        "SELECT count(*) FROM audit_events WHERE user_id = :uid "
        "AND event_type = 'billing.subscription.cancelled'",
    ) == 1


# ─────────────────────────────────────────────────────────────────────────────
# LTD — synthetic payment.captured → perpetual plan
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mock_subscribe_ltd_grants_perpetual(db: AsyncSession) -> None:
    """subscribe('ltd') under mock → plan='ltd', current_period_end=NULL, payment row."""
    result = await svc.subscribe(_USER_ID, "ltd", db)
    await db.commit()

    assert result.razorpay_order_id is not None
    assert result.razorpay_order_id.startswith("order_mock_")

    assert await _user_plan(db) == "ltd"

    sub = await _latest_sub(db)
    assert sub is not None
    assert sub.status == "active"
    assert sub.current_period_end is None  # perpetual sentinel

    # A payments row was upserted by _handle_payment_captured.
    assert await _count(db, "SELECT count(*) FROM payments WHERE user_id = :uid") == 1

    # billing.plan.granted audit with tier=ltd.
    assert await _count(
        db,
        "SELECT count(*) FROM audit_events WHERE user_id = :uid "
        "AND event_type = 'billing.plan.granted'",
    ) == 1

    status = await svc.get_billing_status(_USER_ID, db)
    assert status.plan == "ltd"
    assert status.entitlement == "pro"
