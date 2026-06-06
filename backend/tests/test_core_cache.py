"""Tests for ``app.core.cache`` — versioned keys, single-flight, ETag, prewarm."""

from __future__ import annotations

import asyncio
import hashlib
import uuid

import pytest
import pytest_asyncio

from app.core.cache import etag_for, get_or_set, prewarm_top_categories
from app.shared.config import settings
from app.shared.valkey import get_valkey_cache


@pytest_asyncio.fixture(loop_scope="function")
async def fresh_key(use_live_valkey):  # noqa: F811
    """Yield a unique cache key + clean it before/after the test."""
    key = f"test:{uuid.uuid4()}"
    client = await get_valkey_cache()
    full = f"meesell:{settings.CACHE_VERSION}:{key}"
    await client.delete(full)
    await client.delete(f"{full}:lock")
    yield key
    await client.delete(full)
    await client.delete(f"{full}:lock")


# ── 1. Versioned key format ───────────────────────────────────────────────
@pytest.mark.asyncio
async def test_versioned_key_format(fresh_key):
    """``get_or_set`` writes under ``meesell:v{cache_version}:{key}``."""
    key = fresh_key
    called = {"n": 0}

    async def fetch():
        called["n"] += 1
        return {"hello": "world"}

    value = await get_or_set(key, fetch, ttl=60)
    assert value == {"hello": "world"}
    assert called["n"] == 1

    # Confirm the key landed under the locked prefix.
    client = await get_valkey_cache()
    full = f"meesell:{settings.CACHE_VERSION}:{key}"
    raw = await client.get(full)
    assert raw is not None
    assert "hello" in raw


# ── 2. Miss-then-hit dedupes the fetch ────────────────────────────────────
@pytest.mark.asyncio
async def test_get_or_set_miss_calls_fetch_then_sets(fresh_key):
    key = fresh_key
    n_calls = {"value": 0}

    async def fetch():
        n_calls["value"] += 1
        return ["a", "b", "c"]

    v1 = await get_or_set(key, fetch, ttl=60)
    v2 = await get_or_set(key, fetch, ttl=60)
    assert v1 == ["a", "b", "c"]
    assert v2 == ["a", "b", "c"]
    assert n_calls["value"] == 1  # fetch only called on the first miss


# ── 3. Single-flight dedupes concurrent callers ───────────────────────────
@pytest.mark.asyncio
async def test_get_or_set_single_flight_dedupes(fresh_key):
    """Ten concurrent get_or_set with single_flight=True → fetch called once."""
    key = fresh_key
    n_calls = {"value": 0}
    started = asyncio.Event()
    release = asyncio.Event()

    async def fetch():
        n_calls["value"] += 1
        started.set()
        # Make the elected fetcher slow so concurrent callers must wait/poll.
        await release.wait()
        return {"sf": True}

    async def caller():
        return await get_or_set(key, fetch, ttl=60, single_flight=True)

    tasks = [asyncio.create_task(caller()) for _ in range(10)]
    # Wait for the elected fetcher to start, then release so it finishes.
    await asyncio.wait_for(started.wait(), timeout=2)
    # Give pollers a chance to spin up.
    await asyncio.sleep(0.1)
    release.set()
    results = await asyncio.gather(*tasks)

    assert all(r == {"sf": True} for r in results)
    assert n_calls["value"] == 1


# ── 4. ETag — quoted SHA-256 ──────────────────────────────────────────────
def test_etag_for_quoted_sha256():
    payload = b"hello"
    expected = f'"{hashlib.sha256(payload).hexdigest()}"'
    etag = etag_for(payload)
    assert etag == expected
    # Must be a quoted strong ETag per RFC 7232 §2.3.
    assert etag.startswith('"') and etag.endswith('"')
    # 64 hex chars between the quotes.
    assert len(etag) == 66


# ── 5. Pre-warm stub does not raise ───────────────────────────────────────
@pytest.mark.asyncio
async def test_prewarm_top_categories_stub_no_raise():
    """V1 stub — logs intent + returns None without side effects."""
    result = await prewarm_top_categories()
    assert result is None
    # Call with a custom n too.
    result2 = await prewarm_top_categories(n=10)
    assert result2 is None
