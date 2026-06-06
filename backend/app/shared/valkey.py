"""Async Valkey 8 client factories — DB-scoped, lazy-singleton.

Per BACKEND_ARCHITECTURE.md §5.C, this module exposes **four** factory
functions that select the correct logical Valkey DB.  The factory boundary
IS the DB-allocation enforcement — there is no ``get_valkey(db: int)``
factory by design.

DB allocation (§1.B + §5.C locked)
----------------------------------
============  ====  ======================================================
Factory       DB    Purpose
============  ====  ======================================================
``otp``       0     OTP store, sliding-window RL, sessions,
                    refresh-token allowlist (HMAC-with-pepper keyspace)
``broker``    1     Celery broker
``results``   2     Celery result backend
``cache``     3     Application read-through cache (schemas, enums,
                    category tree, seller-profile)
============  ====  ======================================================

Each factory returns the same pool-backed client across calls (module-level
lazy init).  The TCP connection pool is reused for the lifetime of the
worker process; teardown happens via the same ``app.shutdown`` handler that
disposes the SQL engine.

Refresh-token allowlist Lua script (§5.C FE-D5 lock)
----------------------------------------------------
The Lua script body itself is owned by ``core/auth.py`` (§4.B FE-D5
amendment); this module owns the registration mechanism — :func:`load_lua_script`
calls ``SCRIPT LOAD`` once and returns the SHA1 digest.  Callers cache the
digest and invoke via ``EVALSHA``; on ``NOSCRIPT`` (which only happens after
a Valkey restart flushes the script cache) the caller falls back to plain
``EVAL`` with the literal source — :func:`eval_lua_script` does this transparently.

Locked rule (DB isolation)
--------------------------
Cross-DB access is forbidden.  Rate-limit middleware MUST NOT read DB 3;
``core/cache.py`` MUST NOT read DB 0.  The §1.B topology lock is the
contract; the factory split is its structural enforcement.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse, urlunparse

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import NoScriptError

from app.shared.config import settings

logger = logging.getLogger(__name__)

# ── Per-process lazy singletons ────────────────────────────────────────────
_otp_client: Redis | None = None
_broker_client: Redis | None = None
_results_client: Redis | None = None
_cache_client: Redis | None = None


def _build_url_for_db(base_url: str, db: int) -> str:
    """Replace the database number in a redis:// URL.

    The §5.D ``VALKEY_URL`` convention is **DB-agnostic** — the URL may carry
    any DB suffix (or none); the factories select the correct DB here.
    """
    parsed = urlparse(base_url)
    # path is "/0" or "" depending on whether a DB was in the URL
    return urlunparse(parsed._replace(path=f"/{db}"))


def _make_client(db: int) -> Redis:
    """Create a new async Valkey client pinned to ``db``."""
    url = _build_url_for_db(settings.VALKEY_URL, db)
    return redis.from_url(url, decode_responses=True)


async def get_valkey_otp() -> Redis:
    """DB 0 — OTP, sliding-window RL, sessions, refresh-token allowlist.

    Lazy module-level singleton.  Reuses the same pool across calls.
    """
    global _otp_client
    if _otp_client is None:
        _otp_client = _make_client(0)
    return _otp_client


async def get_valkey_broker() -> Redis:
    """DB 1 — Celery broker.  Consumed by ``workers/celery_app.py`` only."""
    global _broker_client
    if _broker_client is None:
        _broker_client = _make_client(1)
    return _broker_client


async def get_valkey_results() -> Redis:
    """DB 2 — Celery result backend.  Consumed by ``workers/celery_app.py`` only."""
    global _results_client
    if _results_client is None:
        _results_client = _make_client(2)
    return _results_client


async def get_valkey_cache() -> Redis:
    """DB 3 — Application read-through cache.  Consumed by ``core/cache.py`` only."""
    global _cache_client
    if _cache_client is None:
        _cache_client = _make_client(3)
    return _cache_client


# ── Lua script registration ────────────────────────────────────────────────
async def load_lua_script(client: Redis, source: str) -> str:
    """Register ``source`` with the server via ``SCRIPT LOAD``; return digest.

    Per §5.C, the canonical posture is: call this once at process startup,
    cache the returned SHA1 digest on the service singleton, and invoke
    thereafter via :func:`eval_lua_script` (which prefers ``EVALSHA``).

    Args:
        client: Any of the four factory clients (typically the OTP-DB client,
            because the refresh-token Lua script lives in DB 0).
        source: The Lua script source as a string.

    Returns:
        The 40-character hex SHA1 digest returned by ``SCRIPT LOAD``.
    """
    digest: str = await client.script_load(source)
    logger.info("Loaded Lua script (digest=%s, len=%d)", digest, len(source))
    return digest


async def eval_lua_script(
    client: Redis,
    digest: str,
    source: str,
    keys: list[str] | None = None,
    args: list[Any] | None = None,
) -> Any:
    """Invoke a previously-loaded Lua script.

    Tries ``EVALSHA`` first (zero network payload for the script body).
    On ``NoScriptError`` (raised when Valkey returns ``NOSCRIPT`` — happens
    after the server's script cache is flushed by a restart) falls back to
    plain ``EVAL`` with the literal source.

    Args:
        client: The Valkey client (DB-scoped).
        digest: The SHA1 digest returned by :func:`load_lua_script`.
        source: The Lua source, used only on the ``NOSCRIPT`` fallback path.
        keys: Lua ``KEYS[]`` array.  Defaults to empty.
        args: Lua ``ARGV[]`` array.  Defaults to empty.
    """
    keys = keys or []
    args = args or []
    try:
        return await client.evalsha(digest, len(keys), *keys, *args)
    except NoScriptError:
        # Server script cache was flushed (Valkey restart).  Re-load and EVAL
        # with the literal body; subsequent calls will hit EVALSHA again.
        logger.warning("EVALSHA NOSCRIPT — falling back to EVAL (digest=%s)", digest)
        return await client.eval(source, len(keys), *keys, *args)


async def aclose_all() -> None:
    """Close every cached client.  Called from the app-shutdown handler.

    Safe to call when some/all clients have not been initialised.
    """
    global _otp_client, _broker_client, _results_client, _cache_client
    for name, client in (
        ("otp", _otp_client),
        ("broker", _broker_client),
        ("results", _results_client),
        ("cache", _cache_client),
    ):
        if client is not None:
            try:
                await client.aclose()
            except Exception as exc:  # pragma: no cover — best-effort teardown
                logger.warning("Valkey %s client aclose failed: %s", name, exc)
    _otp_client = None
    _broker_client = None
    _results_client = None
    _cache_client = None


__all__ = [
    "get_valkey_otp",
    "get_valkey_broker",
    "get_valkey_results",
    "get_valkey_cache",
    "load_lua_script",
    "eval_lua_script",
    "aclose_all",
]
