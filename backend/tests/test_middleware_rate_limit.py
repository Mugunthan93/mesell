"""Valkey sliding-window rate limiter."""

import uuid

import pytest
import pytest_asyncio
import redis.asyncio as redis
from fastapi import HTTPException

from app.middleware.rate_limit import LIMITS, enforce


@pytest_asyncio.fixture
async def valkey():
    r = redis.from_url("redis://localhost:6379/13", decode_responses=True)
    await r.flushdb()
    yield r
    await r.flushdb()
    await r.aclose()


@pytest.mark.asyncio
async def test_under_budget_allows_request(valkey):
    uid = uuid.uuid4()
    for _ in range(LIMITS["generate"].per_minute):
        await enforce(valkey, uid, "generate")


@pytest.mark.asyncio
async def test_over_budget_returns_429_with_retry_after(valkey):
    uid = uuid.uuid4()
    for _ in range(LIMITS["generate"].per_minute):
        await enforce(valkey, uid, "generate")
    with pytest.raises(HTTPException) as exc:
        await enforce(valkey, uid, "generate")
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers
    assert int(exc.value.headers["Retry-After"]) >= 1


@pytest.mark.asyncio
async def test_unknown_bucket_is_noop(valkey):
    uid = uuid.uuid4()
    for _ in range(100):
        await enforce(valkey, uid, "no-such-bucket")  # must not raise


@pytest.mark.asyncio
async def test_per_user_isolation(valkey):
    uid_a, uid_b = uuid.uuid4(), uuid.uuid4()
    for _ in range(LIMITS["generate"].per_minute):
        await enforce(valkey, uid_a, "generate")
    # B's bucket should still have headroom.
    for _ in range(LIMITS["generate"].per_minute):
        await enforce(valkey, uid_b, "generate")


@pytest.mark.asyncio
async def test_each_bucket_has_its_own_counter(valkey):
    uid = uuid.uuid4()
    # Hammer the "images" bucket — generate must still be unaffected.
    for _ in range(LIMITS["images"].per_minute):
        await enforce(valkey, uid, "images")
    await enforce(valkey, uid, "generate")  # should not raise
