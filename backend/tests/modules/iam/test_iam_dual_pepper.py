"""Dual-pepper grace-window rotation tests (R5, dual-pepper-rotation feature).

These tests verify the versioned allowlist key + dual-pepper read fallback
added to ``app.core.auth`` so a prod ``REFRESH_TOKEN_PEPPER`` rotation can run a
grace window (read ``vN`` then ``vN-1``) instead of a hard cutover that
invalidates every live session at once.

Strategy
--------
ALL tests here run WITHOUT a live Valkey — they use ``fakeredis.aioredis``
(an in-memory async Redis fake) for the read/rotate paths and pure-function
assertions for the key-format paths. No dev tunnel / port-forward is required,
so these run green in plain CI gate 1 (unit). The legacy live-Valkey tests in
``test_core_auth_rotation.py`` are untouched and remain infra-gated.

Settings are mutated via monkeypatch on the singleton ``settings`` instance;
pytest reverts every attr on teardown.
"""

from __future__ import annotations

import hashlib
import hmac

import pytest
import pytest_asyncio
from fakeredis import aioredis as fake_aioredis

pytestmark = pytest.mark.unit

from app.core.auth import (
    REFRESH_ROTATE_LUA,
    _reset_lua_cache_for_tests,
    refresh_allowlist_key,
    rotate_refresh_token,
    validate_refresh_allowlist,
)
from app.shared.config import settings


# NOTE: no module-level ``pytestmark = pytest.mark.asyncio`` — pytest.ini runs
# ``asyncio_mode = auto`` so async tests are awaited automatically and the two
# pure-function tests below stay synchronous (marking them asyncio would warn).


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _expected_digest(token: str, pepper: str) -> str:
    return hmac.new(
        pepper.encode("utf-8"), token.encode("utf-8"), hashlib.sha256
    ).hexdigest()


@pytest_asyncio.fixture(loop_scope="function")
async def fake_valkey():
    """In-memory async Redis fake (decode_responses=True to mirror DB-0 client)."""
    client = fake_aioredis.FakeRedis(decode_responses=True)
    _reset_lua_cache_for_tests()
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture(autouse=True)
def _baseline_pepper(monkeypatch):
    """Pin a deterministic CURRENT pepper/version for every test in this module."""
    monkeypatch.setattr(settings, "REFRESH_TOKEN_PEPPER", "pepper-current", raising=False)
    monkeypatch.setattr(settings, "REFRESH_TOKEN_PEPPER_VERSION", 2, raising=False)
    monkeypatch.setattr(settings, "REFRESH_TOKEN_PEPPER_PREVIOUS", "", raising=False)


# ─────────────────────────────────────────────────────────────────────────────
# 1 + 2 — versioned key format (pure functions, no Redis)
# ─────────────────────────────────────────────────────────────────────────────
def test_versioned_key_format(monkeypatch):
    """refresh_allowlist_key(version=N) → cache:refresh:vN:{digest}."""
    monkeypatch.setattr(settings, "REFRESH_TOKEN_PEPPER", "pepper-current", raising=False)
    key = refresh_allowlist_key("tok", version=2)
    expected = f"cache:refresh:v2:{_expected_digest('tok', 'pepper-current')}"
    assert key == expected
    assert key.startswith("cache:refresh:v2:")


def test_versioned_key_default_version(monkeypatch):
    """Default call uses settings.REFRESH_TOKEN_PEPPER_VERSION as the vN tag."""
    monkeypatch.setattr(settings, "REFRESH_TOKEN_PEPPER", "pepper-current", raising=False)
    monkeypatch.setattr(settings, "REFRESH_TOKEN_PEPPER_VERSION", 5, raising=False)
    key = refresh_allowlist_key("tok")
    expected = f"cache:refresh:v5:{_expected_digest('tok', 'pepper-current')}"
    assert key == expected


# ─────────────────────────────────────────────────────────────────────────────
# 3-6 — dual-pepper read fallback (fakeredis)
# ─────────────────────────────────────────────────────────────────────────────
async def test_dual_read_primary_hit(fake_valkey, monkeypatch):
    """CURRENT key present → returned; PREVIOUS pepper set but NOT consulted."""
    monkeypatch.setattr(settings, "REFRESH_TOKEN_PEPPER_PREVIOUS", "pepper-old", raising=False)

    token = "tok-primary"
    primary_key = refresh_allowlist_key(token)  # current pepper / v2
    await fake_valkey.set(primary_key, '{"user_id":"u1"}')

    result = await validate_refresh_allowlist(fake_valkey, token)
    assert result is not None
    matched_key, value = result
    assert matched_key == primary_key
    assert value == '{"user_id":"u1"}'


async def test_dual_read_fallback_hit(fake_valkey, monkeypatch):
    """Primary absent, PREVIOUS pepper set, vN-1 key present → fallback returns it."""
    monkeypatch.setattr(settings, "REFRESH_TOKEN_PEPPER_PREVIOUS", "pepper-old", raising=False)

    token = "tok-fallback"
    # Write ONLY the previous-pepper key at version N-1 (= 1).
    fallback_key = refresh_allowlist_key(token, pepper="pepper-old", version=1)
    await fake_valkey.set(fallback_key, '{"user_id":"u2"}')

    # Sanity: the primary (current-pepper) key is genuinely absent.
    assert await fake_valkey.get(refresh_allowlist_key(token)) is None

    result = await validate_refresh_allowlist(fake_valkey, token)
    assert result is not None
    matched_key, value = result
    assert matched_key == fallback_key
    assert matched_key.startswith("cache:refresh:v1:")
    assert value == '{"user_id":"u2"}'


async def test_dual_read_miss_when_no_previous(fake_valkey):
    """PREVIOUS pepper empty + primary absent → None, no fallback attempt."""
    # _baseline_pepper leaves REFRESH_TOKEN_PEPPER_PREVIOUS = "".
    assert settings.REFRESH_TOKEN_PEPPER_PREVIOUS == ""
    result = await validate_refresh_allowlist(fake_valkey, "tok-missing")
    assert result is None


async def test_dual_read_miss_both_absent(fake_valkey, monkeypatch):
    """Both keys absent even with PREVIOUS set → None."""
    monkeypatch.setattr(settings, "REFRESH_TOKEN_PEPPER_PREVIOUS", "pepper-old", raising=False)
    result = await validate_refresh_allowlist(fake_valkey, "tok-nowhere")
    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# 7 — rotation uses versioned keys + replay protection still holds
# ─────────────────────────────────────────────────────────────────────────────
async def test_rotate_uses_versioned_keys(fake_valkey, monkeypatch):
    """rotate_refresh_token with helper-derived versioned keys → 1, replay → 0.

    fakeredis 2.x ships without a Lua interpreter (no SCRIPT LOAD / EVAL), so
    we substitute the ``eval_lua_script`` helper with a pure-Python executor
    that reproduces REFRESH_ROTATE_LUA's exact semantics (GET KEYS[1]; if set,
    DEL it + SET KEYS[2]=ARGV[1] EX ARGV[2], return 1; else return 0) against
    the same fakeredis instance. This verifies test 7's intent — that
    ``rotate_refresh_token`` composes the *versioned* KEYS[1]/KEYS[2] correctly
    and that replay protection (return 0 on a missing old key) holds — without
    needing a Lua VM. The actual Lua execution + SCRIPT-LOAD caching is covered
    by the live-Valkey ``test_core_auth_rotation.py`` suite.
    """
    import app.core.auth as _auth_mod

    async def _fake_load(client, source):
        assert source == REFRESH_ROTATE_LUA  # exact script body, unchanged
        return "0" * 40

    async def _fake_eval(client, digest, source, *, keys, args):
        old_key, new_key = keys
        new_value, ttl = args
        if await client.get(old_key) is not None:
            await client.delete(old_key)
            await client.set(new_key, new_value, ex=int(ttl))
            return 1
        return 0

    monkeypatch.setattr(_auth_mod, "load_lua_script", _fake_load)
    monkeypatch.setattr(_auth_mod, "eval_lua_script", _fake_eval)
    _reset_lua_cache_for_tests()

    old_key = refresh_allowlist_key("tok-old")  # current pepper / v2
    new_key = refresh_allowlist_key("tok-new")
    assert old_key.startswith("cache:refresh:v2:")
    assert new_key.startswith("cache:refresh:v2:")

    # Seed the old entry, then rotate.
    await fake_valkey.set(old_key, '{"user_id":"u3"}')
    rotated = await rotate_refresh_token(
        fake_valkey,
        old_key=old_key,
        new_key=new_key,
        new_value='{"user_id":"u3","issued_at":1}',
        ttl_seconds=300,
    )
    assert rotated is True
    # Old key gone, new key present.
    assert await fake_valkey.get(old_key) is None
    assert await fake_valkey.get(new_key) == '{"user_id":"u3","issued_at":1}'

    # Replay: re-presenting the (now-deleted) old key returns 0 (no rotation).
    replay = await rotate_refresh_token(
        fake_valkey,
        old_key=old_key,
        new_key=refresh_allowlist_key("tok-replay"),
        new_value='{"user_id":"u3"}',
        ttl_seconds=300,
    )
    assert replay is False


# ─────────────────────────────────────────────────────────────────────────────
# 8 — single-pepper mode issues exactly one GET (no fallback round-trip)
# ─────────────────────────────────────────────────────────────────────────────
async def test_single_pepper_mode_unchanged(fake_valkey, monkeypatch):
    """PEPPER_PREVIOUS="" → validate_refresh_allowlist issues exactly ONE GET."""
    # _baseline_pepper already sets PREVIOUS="". Count GET calls.
    calls: list[str] = []
    real_get = fake_valkey.get

    async def counting_get(key, *a, **kw):
        calls.append(key)
        return await real_get(key, *a, **kw)

    monkeypatch.setattr(fake_valkey, "get", counting_get)

    result = await validate_refresh_allowlist(fake_valkey, "tok-single")
    assert result is None  # nothing stored
    assert len(calls) == 1, f"expected exactly 1 GET in single-pepper mode, got {calls}"
    assert calls[0] == refresh_allowlist_key("tok-single")
