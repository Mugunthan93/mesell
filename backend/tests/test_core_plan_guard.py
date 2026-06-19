"""Tests for ``app.core.plan_guard``.

Sliding-hour resources hit live Valkey DB 0; ``product_count`` is
covered by patching the COUNT(*) query to avoid Postgres dependency in
the unit-test path.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from app.core.plan_guard import (
    V1_LIMITS_FREE,
    PlanLimitExceededError,
    enforce_plan_limit,
)
from app.shared.valkey import get_valkey_otp

pytestmark = pytest.mark.integration


# ── Fixture: wipe per-user plan keys before + after each test ─────────────
@pytest_asyncio.fixture(loop_scope="function")
async def plan_user_id(use_live_valkey):  # noqa: F811 — fixture chaining
    uid = uuid.uuid4()
    client = await get_valkey_otp()
    # Clean slate before the test in case a previous run left state.
    for resource in V1_LIMITS_FREE:
        try:
            await client.delete(f"plan:{uid}:{resource}")
        except Exception:
            pass
    yield uid
    # Cleanup after.
    for resource in V1_LIMITS_FREE:
        try:
            await client.delete(f"plan:{uid}:{resource}")
        except Exception:
            pass


# ── 1. Sliding-window resources — happy path + overflow ───────────────────
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "resource",
    ["ai_autofill_hourly", "smart_picker_hourly", "create_product_hourly"],
)
async def test_sliding_window_at_limit_passes(plan_user_id, resource):
    uid = plan_user_id
    limit, _ = V1_LIMITS_FREE[resource]
    # Reserve up to the limit, one at a time.
    for _ in range(limit):
        await enforce_plan_limit(uid, "free", resource)
    # The next call MUST raise.
    with pytest.raises(PlanLimitExceededError) as exc_info:
        await enforce_plan_limit(uid, "free", resource)
    assert exc_info.value.resource == resource
    assert exc_info.value.limit == limit
    assert exc_info.value.current == limit
    assert exc_info.value.status_code == 402
    assert exc_info.value.code == "plan.limit_exceeded"


@pytest.mark.asyncio
async def test_sliding_window_requested_batch(plan_user_id):
    """``requested`` argument reserves N slots in one call."""
    uid = plan_user_id
    # ai_autofill_hourly limit=50; request 10 → OK; request 41 → overflow.
    await enforce_plan_limit(uid, "free", "ai_autofill_hourly", requested=10)
    with pytest.raises(PlanLimitExceededError):
        await enforce_plan_limit(uid, "free", "ai_autofill_hourly", requested=41)


@pytest.mark.asyncio
async def test_sliding_window_recovers_after_trim(plan_user_id):
    """After we manually purge the sorted set, the gate opens again."""
    uid = plan_user_id
    limit, _ = V1_LIMITS_FREE["create_product_hourly"]
    for _ in range(limit):
        await enforce_plan_limit(uid, "free", "create_product_hourly")
    client = await get_valkey_otp()
    await client.delete(f"plan:{uid}:create_product_hourly")
    # Now allowed again.
    await enforce_plan_limit(uid, "free", "create_product_hourly")


# ── 2. product_count — total cap via mocked DB ────────────────────────────
# NOTE: with a real ``db`` session, ``enforce_plan_limit`` resolves entitlement
# DB-fresh (F7).  These free-path unit tests stub BOTH the entitlement read (a
# free User row with no trial / no sub) and the COUNT(*) query on the same mock
# ``db.execute``.  ``db.get`` returns the free user; the two ``execute`` calls
# (latest-sub lookup inside resolve_entitlement, then COUNT(*)) are sequenced.


def _free_user_mock():
    """A users-row mock that resolves to the 'free' entitlement."""
    user = MagicMock()
    user.plan = "free"
    user.trial_ends_at = None
    return user


@pytest.mark.asyncio
@pytest.mark.unit
async def test_product_count_under_limit_passes():
    uid = uuid.uuid4()
    mock_db = MagicMock()
    # resolve_entitlement: db.get(User, uid) → free user (no trial).  The free
    # (no-trial) path returns BEFORE any sub lookup, so the only execute() is
    # the COUNT(*) inside _enforce_total_cap.
    mock_db.get = AsyncMock(return_value=_free_user_mock())
    count_res = MagicMock()
    count_res.scalar_one.return_value = 30
    mock_db.execute = AsyncMock(return_value=count_res)
    # Should not raise — 30 < 50 (the founder-ruled Free SKU cap).
    await enforce_plan_limit(uid, "free", "product_count", db=mock_db)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_product_count_at_limit_raises():
    """Free SKU cap is 50 (founder ruling 2026-06-19; corrects 100 drift)."""
    uid = uuid.uuid4()
    mock_db = MagicMock()
    mock_db.get = AsyncMock(return_value=_free_user_mock())
    count_res = MagicMock()
    count_res.scalar_one.return_value = 50  # at the cap; +1 overflows
    mock_db.execute = AsyncMock(return_value=count_res)
    with pytest.raises(PlanLimitExceededError) as exc_info:
        await enforce_plan_limit(uid, "free", "product_count", db=mock_db)
    assert exc_info.value.resource == "product_count"
    assert exc_info.value.limit == 50
    assert exc_info.value.current == 50


@pytest.mark.asyncio
@pytest.mark.unit
async def test_product_count_requires_db_kwarg():
    uid = uuid.uuid4()
    with pytest.raises(ValueError, match="requires db"):
        await enforce_plan_limit(uid, "free", "product_count")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_unknown_resource_raises():
    uid = uuid.uuid4()
    with pytest.raises(ValueError, match="unknown resource"):
        await enforce_plan_limit(uid, "free", "no_such_resource")  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────────────
# Razorpay Wave 3 — resolve_entitlement truth table (§8.13) + tier-aware
# enforce_plan_limit (§8.14).  All UNIT (mocked db) — no live Postgres needed.
# ─────────────────────────────────────────────────────────────────────────────
from datetime import datetime, timedelta, timezone  # noqa: E402

from app.core.plan_guard import resolve_entitlement  # noqa: E402

_NOW = datetime.now(timezone.utc)


def _user(plan="free", trial_ends_at=None):
    u = MagicMock()
    u.plan = plan
    u.trial_ends_at = trial_ends_at
    return u


def _sub(status, current_period_end=None):
    s = MagicMock()
    s.status = status
    s.current_period_end = current_period_end
    return s


def _db_for(user, sub=None):
    """A mock AsyncSession where ``get`` returns ``user`` and the first
    ``execute`` (latest-sub lookup) returns ``sub``."""
    db = MagicMock()
    db.get = AsyncMock(return_value=user)
    sub_res = MagicMock()
    sub_res.scalar_one_or_none.return_value = sub
    db.execute = AsyncMock(return_value=sub_res)
    return db


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.parametrize(
    "plan,trial_ends_at,sub,expected",
    [
        # plain free → free
        ("free", None, None, "free"),
        # free + live trial → pro (the 14-day trial)
        ("free", _NOW + timedelta(days=5), None, "pro"),
        # free + expired trial → free
        ("free", _NOW - timedelta(days=1), None, "free"),
        # starter + active sub → starter
        ("starter", None, _sub("active"), "starter"),
        # pro + active sub → pro
        ("pro", None, _sub("active"), "pro"),
        # pro_annual + active sub → pro (annual collapses to base)
        ("pro_annual", None, _sub("active"), "pro"),
        # business + active sub → business
        ("business", None, _sub("active"), "business"),
        # business_annual + active sub → business
        ("business_annual", None, _sub("active"), "business"),
        # ltd → pro perpetual (no sub-period check needed)
        ("ltd", None, _sub("active", None), "pro"),
        # pro + active sub + trial set → pro (paid wins over trial)
        ("pro", _NOW + timedelta(days=5), _sub("active"), "pro"),
        # paid plan but HALTED sub → free (defensive)
        ("pro", None, _sub("halted"), "free"),
        # paid plan but NO sub row → free (defensive)
        ("pro", None, None, "free"),
        # cancelled sub BEFORE period end → still entitled
        ("pro", None, _sub("cancelled", _NOW + timedelta(days=3)), "pro"),
        # cancelled sub AFTER period end → free
        ("pro", None, _sub("cancelled", _NOW - timedelta(days=1)), "free"),
    ],
)
async def test_resolve_entitlement_truth_table(plan, trial_ends_at, sub, expected):
    uid = uuid.uuid4()
    db = _db_for(_user(plan, trial_ends_at), sub)
    result = await resolve_entitlement(user_id=uid, db=db)
    assert result == expected


@pytest.mark.asyncio
@pytest.mark.unit
async def test_resolve_entitlement_missing_user_is_free():
    """A vanished principal fails closed to the least-privileged tier."""
    uid = uuid.uuid4()
    db = MagicMock()
    db.get = AsyncMock(return_value=None)
    assert await resolve_entitlement(user_id=uid, db=db) == "free"


# ── Tier-aware enforce_plan_limit (§8.14) ────────────────────────────────────
def _db_entitled_then_count(user, sub, count):
    """Mock db: db.get→user; execute() #1 (sub lookup), #2 (COUNT(*))."""
    db = MagicMock()
    db.get = AsyncMock(return_value=user)
    sub_res = MagicMock()
    sub_res.scalar_one_or_none.return_value = sub
    count_res = MagicMock()
    count_res.scalar_one.return_value = count
    db.execute = AsyncMock(side_effect=[sub_res, count_res])
    return db


@pytest.mark.asyncio
@pytest.mark.unit
async def test_starter_product_count_blocks_at_150():
    """Starter SKU cap = 150 → the 151st is blocked."""
    uid = uuid.uuid4()
    db = _db_entitled_then_count(_user("starter"), _sub("active"), 150)
    with pytest.raises(PlanLimitExceededError) as exc_info:
        await enforce_plan_limit(uid, "free", "product_count", db=db)
    assert exc_info.value.limit == 150
    assert exc_info.value.current == 150


@pytest.mark.asyncio
@pytest.mark.unit
async def test_starter_product_count_under_150_passes():
    uid = uuid.uuid4()
    db = _db_entitled_then_count(_user("starter"), _sub("active"), 149)
    await enforce_plan_limit(uid, "free", "product_count", db=db)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_pro_product_count_unlimited_not_blocked():
    """Pro is UNLIMITED → the cap is skipped even at 10,000 products.

    Only ONE execute() is expected (the sub lookup) because the UNLIMITED
    branch returns BEFORE the COUNT(*) — assert COUNT was never issued.
    """
    uid = uuid.uuid4()
    db = MagicMock()
    db.get = AsyncMock(return_value=_user("pro"))
    sub_res = MagicMock()
    sub_res.scalar_one_or_none.return_value = _sub("active")
    db.execute = AsyncMock(return_value=sub_res)
    # Must NOT raise; the COUNT(*) path is never reached for unlimited tiers.
    await enforce_plan_limit(uid, "free", "product_count", db=db)
    assert db.execute.await_count == 1  # sub lookup only, no COUNT(*)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_business_product_count_unlimited_not_blocked():
    uid = uuid.uuid4()
    db = MagicMock()
    db.get = AsyncMock(return_value=_user("business"))
    sub_res = MagicMock()
    sub_res.scalar_one_or_none.return_value = _sub("active")
    db.execute = AsyncMock(return_value=sub_res)
    await enforce_plan_limit(uid, "free", "product_count", db=db)
    assert db.execute.await_count == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_trialist_gets_pro_unlimited_product_count():
    """A free user on a live trial gets Pro entitlement → unlimited SKUs."""
    uid = uuid.uuid4()
    db = MagicMock()
    db.get = AsyncMock(
        return_value=_user("free", trial_ends_at=_NOW + timedelta(days=5))
    )
    sub_res = MagicMock()
    sub_res.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=sub_res)
    # Trial → pro → unlimited; no COUNT(*) issued. (db.execute may be 0 here:
    # free-plan + trial path in resolve_entitlement does NOT query a sub.)
    await enforce_plan_limit(uid, "free", "product_count", db=db)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_free_fallback_without_db_unchanged():
    """No db → fallback to the 'free' hint; ValueError on product_count (free
    cap is a total cap needing db) — proves the free path is unchanged."""
    uid = uuid.uuid4()
    with pytest.raises(ValueError, match="requires db"):
        await enforce_plan_limit(uid, "free", "product_count")
