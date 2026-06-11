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
@pytest.mark.asyncio
@pytest.mark.unit
async def test_product_count_under_limit_passes():
    uid = uuid.uuid4()
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 50
    mock_db.execute = AsyncMock(return_value=mock_result)
    # Should not raise — 50 < 100.
    await enforce_plan_limit(uid, "free", "product_count", db=mock_db)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_product_count_at_limit_raises():
    uid = uuid.uuid4()
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 100  # at the cap; +1 overflows
    mock_db.execute = AsyncMock(return_value=mock_result)
    with pytest.raises(PlanLimitExceededError) as exc_info:
        await enforce_plan_limit(uid, "free", "product_count", db=mock_db)
    assert exc_info.value.resource == "product_count"
    assert exc_info.value.limit == 100
    assert exc_info.value.current == 100


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
