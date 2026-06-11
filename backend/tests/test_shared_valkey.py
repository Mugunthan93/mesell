"""§5.C acceptance tests — shared.valkey factories + Lua helpers.

Verifies the locked surface area:
  * Four DB-scoped factories — ``get_valkey_otp`` (DB 0), ``get_valkey_broker``
    (DB 1), ``get_valkey_results`` (DB 2), ``get_valkey_cache`` (DB 3).
  * Each factory returns a pool-backed lazy singleton.
  * ``load_lua_script`` calls ``SCRIPT LOAD``; ``eval_lua_script`` prefers
    ``EVALSHA`` with ``EVAL`` fallback on ``NOSCRIPT``.

These tests run with a mocked ``redis.from_url`` so they do not require a
live Valkey — DB-allocation enforcement is structural (the URL the factory
asks for IS the verification).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse

import pytest
from redis.exceptions import NoScriptError

from app.shared import valkey as valkey_mod
from app.shared.valkey import (
    eval_lua_script,
    get_valkey_broker,
    get_valkey_cache,
    get_valkey_otp,
    get_valkey_results,
    load_lua_script,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset_singletons() -> None:
    """Reset module-level lazy singletons between tests."""
    valkey_mod._otp_client = None
    valkey_mod._broker_client = None
    valkey_mod._results_client = None
    valkey_mod._cache_client = None
    yield
    valkey_mod._otp_client = None
    valkey_mod._broker_client = None
    valkey_mod._results_client = None
    valkey_mod._cache_client = None


# ───────────────────────────────────────────────────────────────────────────
# DB allocation — each factory MUST pin the right DB number
# ───────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("factory", "expected_db"),
    [
        (get_valkey_otp, 0),
        (get_valkey_broker, 1),
        (get_valkey_results, 2),
        (get_valkey_cache, 3),
    ],
)
async def test_factory_pins_correct_db(factory, expected_db: int) -> None:
    """Each factory MUST construct a client URL with the right DB number.

    Locked enforcement of the §1.B topology lock (§5.C).
    """
    captured_urls: list[str] = []

    def _mock_from_url(url: str, **_: object) -> object:
        captured_urls.append(url)
        return MagicMock(name="redis-client")

    with patch("app.shared.valkey.redis.from_url", side_effect=_mock_from_url):
        await factory()

    assert len(captured_urls) == 1
    parsed = urlparse(captured_urls[0])
    assert parsed.path == f"/{expected_db}", (
        f"factory {factory.__name__} MUST pin DB {expected_db}, "
        f"got URL path {parsed.path!r}"
    )


# ───────────────────────────────────────────────────────────────────────────
# Lazy singleton — same client returned across calls within a process
# ───────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_factory_returns_same_client_across_calls() -> None:
    """Lazy singleton — repeat calls reuse the same client per process (§5.C)."""
    construct_count = [0]

    def _mock_from_url(url: str, **_: object) -> object:
        construct_count[0] += 1
        return MagicMock(name=f"client-{construct_count[0]}")

    with patch("app.shared.valkey.redis.from_url", side_effect=_mock_from_url):
        c1 = await get_valkey_otp()
        c2 = await get_valkey_otp()
        c3 = await get_valkey_otp()

    assert c1 is c2 is c3
    assert construct_count[0] == 1, "from_url MUST be called exactly once"


@pytest.mark.asyncio
async def test_factories_are_independent_clients() -> None:
    """Distinct factories return distinct clients (no cross-DB sharing)."""

    def _mock_from_url(url: str, **_: object) -> object:
        return MagicMock(name=f"client-for-{url}")

    with patch("app.shared.valkey.redis.from_url", side_effect=_mock_from_url):
        otp = await get_valkey_otp()
        broker = await get_valkey_broker()
        results = await get_valkey_results()
        cache = await get_valkey_cache()

    # All four MUST be distinct objects
    assert len({id(otp), id(broker), id(results), id(cache)}) == 4


# ───────────────────────────────────────────────────────────────────────────
# Lua script registration + EVALSHA / EVAL fallback
# ───────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_load_lua_script_calls_script_load() -> None:
    """load_lua_script invokes ``SCRIPT LOAD`` and returns the SHA1 digest."""
    client = MagicMock()
    client.script_load = AsyncMock(return_value="deadbeef" * 5)
    source = "return 1"

    digest = await load_lua_script(client, source)

    client.script_load.assert_awaited_once_with(source)
    assert digest == "deadbeef" * 5


@pytest.mark.asyncio
async def test_eval_lua_script_prefers_evalsha() -> None:
    """Happy path — EVALSHA succeeds; EVAL is NOT called (§5.C posture)."""
    client = MagicMock()
    client.evalsha = AsyncMock(return_value=42)
    client.eval = AsyncMock(return_value=99)

    result = await eval_lua_script(
        client,
        digest="abc123",
        source="return 1",
        keys=["k1"],
        args=["a1", "a2"],
    )

    assert result == 42
    client.evalsha.assert_awaited_once_with("abc123", 1, "k1", "a1", "a2")
    client.eval.assert_not_awaited()


@pytest.mark.asyncio
async def test_eval_lua_script_falls_back_to_eval_on_noscript() -> None:
    """Fallback path — Valkey returned ``NOSCRIPT``; EVAL with literal body fires."""
    client = MagicMock()
    client.evalsha = AsyncMock(side_effect=NoScriptError("NOSCRIPT"))
    client.eval = AsyncMock(return_value=7)

    source = "return ARGV[1]"
    result = await eval_lua_script(
        client,
        digest="abc123",
        source=source,
        keys=[],
        args=["hello"],
    )

    assert result == 7
    client.evalsha.assert_awaited_once_with("abc123", 0, "hello")
    client.eval.assert_awaited_once_with(source, 0, "hello")


@pytest.mark.asyncio
async def test_aclose_all_disposes_only_initialised_clients() -> None:
    """aclose_all closes every cached client and tolerates uninitialised ones."""

    def _mock_from_url(url: str, **_: object) -> object:
        client = MagicMock(name=f"client-for-{url}")
        client.aclose = AsyncMock()
        return client

    with patch("app.shared.valkey.redis.from_url", side_effect=_mock_from_url):
        # Only initialise OTP + cache; broker + results stay None
        otp = await get_valkey_otp()
        cache = await get_valkey_cache()

        await valkey_mod.aclose_all()

    otp.aclose.assert_awaited_once()
    cache.aclose.assert_awaited_once()
    # Singletons reset to None
    assert valkey_mod._otp_client is None
    assert valkey_mod._cache_client is None
