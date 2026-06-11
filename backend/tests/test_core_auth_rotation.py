"""Live-Valkey tests for the atomic refresh-token-rotation Lua script per §4.B.

These tests hit the dev Valkey (port-forwarded from the K3s pod — typically
``localhost:6380``, redirected to DB 15 for test isolation via the
``conftest`` env defaults).

The test isolation strategy: every test prefixes its keys with a unique UUID
so concurrent runs in CI cannot collide; teardown deletes the keys.
"""

from __future__ import annotations

import json
import os
import uuid

import pytest
import pytest_asyncio
import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.auth import (
    REFRESH_ROTATE_LUA,
    _reset_lua_cache_for_tests,
    rotate_refresh_token,
)

pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(loop_scope="function")
async def valkey() -> Redis:
    """Async Valkey client pinned to the test DB (``VALKEY_URL`` env, default DB 15).

    The conftest sets ``VALKEY_URL=redis://localhost:6381/15`` by default; on
    the founder's laptop the dev port-forward exposes Valkey on 6380 — both
    map to the same instance with a dedicated test DB.

    ``loop_scope="function"`` is set explicitly so the redis-py asyncio
    Protocol + its Futures are attached to the same function-scoped event
    loop that pytest-asyncio 0.24 uses to run each test (the conftest
    declares ``asyncio_default_fixture_loop_scope=session`` which would
    otherwise mismatch — same pattern as the ``db`` fixture).
    """
    url = os.environ.get("VALKEY_URL", "redis://localhost:6381/15")
    client: Redis = redis.from_url(url, decode_responses=True)
    # Reset the module-level SHA cache so each test starts from a clean slate
    # and exercises the SCRIPT LOAD path on its first call.
    _reset_lua_cache_for_tests()
    try:
        # Cheap reachability probe — skip the test if the dev Valkey is not
        # port-forwarded in this developer's environment.
        await client.ping()
    except Exception as exc:  # noqa: BLE001
        await client.aclose()
        pytest.skip(f"Valkey unreachable at {url} — skipping rotation tests ({exc})")
    try:
        yield client
    finally:
        await client.aclose()


@pytest_asyncio.fixture
def keyprefix() -> str:
    """Per-test key namespace — prevents cross-test collisions."""
    return f"test:rotate:{uuid.uuid4().hex}:"


# ─────────────────────────────────────────────────────────────────────────────
# 14. atomic swap on existing key
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_rotate_refresh_token_atomic_swap(valkey: Redis, keyprefix: str) -> None:
    """Pre-existing old key → rotate → old absent, new present with new value + TTL."""
    old_key = f"{keyprefix}old"
    new_key = f"{keyprefix}new"
    old_value = json.dumps({"user_id": str(uuid.uuid4()), "issued_at": 1, "ip": "1.1.1.1"})
    new_value = json.dumps({"user_id": str(uuid.uuid4()), "issued_at": 2, "ip": "2.2.2.2"})

    try:
        # Seed the old allowlist entry.
        await valkey.set(old_key, old_value, ex=600)
        assert await valkey.get(old_key) == old_value

        # Rotate.
        rotated = await rotate_refresh_token(
            valkey,
            old_key=old_key,
            new_key=new_key,
            new_value=new_value,
            ttl_seconds=300,
        )
        assert rotated is True, "rotation must return True when old key existed"

        # Old key gone.
        assert await valkey.get(old_key) is None, "old allowlist entry must be deleted"

        # New key present with new value.
        assert await valkey.get(new_key) == new_value

        # TTL within (0, 300].
        ttl = await valkey.ttl(new_key)
        assert 0 < ttl <= 300, f"new key TTL out of range: {ttl}"
    finally:
        await valkey.delete(old_key, new_key)


# ─────────────────────────────────────────────────────────────────────────────
# 15. replay attack — old key never set → rotation refuses + nothing written
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_rotate_refresh_token_old_missing_returns_false(
    valkey: Redis, keyprefix: str
) -> None:
    """No old key in store → rotate returns False AND new key is NOT created."""
    old_key = f"{keyprefix}old"
    new_key = f"{keyprefix}new"
    new_value = json.dumps({"user_id": str(uuid.uuid4()), "issued_at": 0, "ip": "9.9.9.9"})

    try:
        # Ensure both keys absent.
        await valkey.delete(old_key, new_key)
        assert await valkey.get(old_key) is None
        assert await valkey.get(new_key) is None

        rotated = await rotate_refresh_token(
            valkey,
            old_key=old_key,
            new_key=new_key,
            new_value=new_value,
            ttl_seconds=300,
        )
        # Per §4.B: replay-attack mitigation — re-presenting a rotated cookie
        # returns False here.
        assert rotated is False

        # And the new key must NOT have been written — a replay attempt cannot
        # smuggle in a new allowlist entry.
        assert await valkey.get(new_key) is None, (
            "new key must not be written when old key absent (replay mitigation)"
        )
    finally:
        await valkey.delete(old_key, new_key)


# ─────────────────────────────────────────────────────────────────────────────
# 16. EVALSHA path then EVAL-fallback path after SCRIPT FLUSH
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_rotate_refresh_token_evalsha_then_eval_fallback(
    valkey: Redis, keyprefix: str
) -> None:
    """Cover both the EVALSHA hot path AND the EVAL fallback after SCRIPT FLUSH.

    Per ``app.shared.valkey.eval_lua_script``: on ``NOSCRIPT`` (returned by
    Valkey when SCRIPT FLUSH has cleared the cache, e.g. after a restart), the
    helper transparently falls back to plain EVAL with the literal source.
    This test exercises both paths within one Python process.
    """
    # ── First rotation — triggers SCRIPT LOAD then EVALSHA. ────────────────
    old1 = f"{keyprefix}old1"
    new1 = f"{keyprefix}new1"
    val1 = json.dumps({"phase": "evalsha", "rid": uuid.uuid4().hex})

    try:
        await valkey.set(old1, val1, ex=600)
        rotated = await rotate_refresh_token(
            valkey, old_key=old1, new_key=new1, new_value=val1, ttl_seconds=300
        )
        assert rotated is True
        assert await valkey.get(new1) == val1
    finally:
        await valkey.delete(old1, new1)

    # ── SCRIPT FLUSH — clears the server-side script cache. ────────────────
    # The next EVALSHA will return NOSCRIPT, and ``eval_lua_script`` must
    # transparently fall back to EVAL.
    await valkey.script_flush()

    # ── Second rotation — exercises the EVAL fallback. ─────────────────────
    old2 = f"{keyprefix}old2"
    new2 = f"{keyprefix}new2"
    val2 = json.dumps({"phase": "eval_fallback", "rid": uuid.uuid4().hex})

    try:
        await valkey.set(old2, val2, ex=600)
        rotated = await rotate_refresh_token(
            valkey, old_key=old2, new_key=new2, new_value=val2, ttl_seconds=300
        )
        assert rotated is True, "EVAL fallback must succeed after SCRIPT FLUSH"
        assert await valkey.get(new2) == val2
        assert await valkey.get(old2) is None
    finally:
        await valkey.delete(old2, new2)


# ─────────────────────────────────────────────────────────────────────────────
# Bonus: the Lua source itself is what we think it is — fast sanity check
# ─────────────────────────────────────────────────────────────────────────────


def test_refresh_rotate_lua_shape() -> None:
    """The Lua script body must compose: GET → DEL → SET EX → return 1, else 0."""
    src = REFRESH_ROTATE_LUA
    assert "redis.call('GET', KEYS[1])" in src
    assert "redis.call('DEL', KEYS[1])" in src
    assert "redis.call('SET', KEYS[2], ARGV[1], 'EX', ARGV[2])" in src
    assert "return 1" in src and "return 0" in src
