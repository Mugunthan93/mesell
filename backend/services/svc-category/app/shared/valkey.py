"""svc-category async Valkey 8 client factories — DB-scoped, lazy-singleton.

Vendored from the monolith ``app.shared.valkey`` (BACKEND_ARCHITECTURE.md
§5.C), TRIMMED to the factories svc-category actually consumes:

* :func:`get_valkey_otp` (DB 0) — the per-IP / per-route rate-limit sliding
  windows (vendored rate_limit_mw), the ``smart_picker_hourly`` plan-guard
  counter (vendored plan_guard), the refresh-allowlist Lua mechanism
  (vendored core/auth.py, dormant — verify-only), AND the SHARED ai_ops
  budget brake.

  **THE BUDGET-BRAKE CARVE-OUT (F3.c / R1):** the budget keys
  ``ai:cost:daily:{date}`` / ``ai:cost:pending:{date}`` /
  ``ai:budget:reservation:{id}`` / ``ai:cost:user:{uid}:hourly:{hr}`` are
  built as LITERAL strings by the vendored ``ai_ops.budget_cap`` +
  ``ai_ops.cost_tracker`` against THIS DB-0 client.  They are UN-prefixed and
  GLOBAL so the ₹500/day cap is SHARED across all services.  This module
  applies NO ``category:`` prefix to DB-0 keys.  Do NOT add one — splitting
  the keyspace per-service breaks the global cap (R1).

* :func:`get_valkey_cache` (DB 3) — the read-through application cache
  (``core/cache.py``).  This is category's OWN keyspace; its keys DO get the
  ``category:`` §2.E namespace prefix — but that prefix is applied in
  ``core/cache.py``'s ``_versioned_key`` (the sole DB-3 consumer), NOT here,
  so the prefix boundary is co-located with the cache-key construction and
  can never leak onto the DB-0 budget keys.

The Lua helpers (:func:`load_lua_script` / :func:`eval_lua_script`) are
vendored verbatim — the vendored ``core/auth.py`` registers the refresh
allowlist Lua via them (dormant in a verify-only service, but the symbol
must resolve).

The factory boundary IS the DB-allocation enforcement (§1.B topology lock).
The Celery broker (DB 1) + result backend (DB 2) factories are NOT vendored —
category runs no worker.
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
_cache_client: Redis | None = None


def _build_url_for_db(base_url: str, db: int) -> str:
    """Replace the database number in a redis:// URL.

    The ``VALKEY_URL`` convention is DB-agnostic — the URL may carry any DB
    suffix (or none); the factory selects the correct DB here.
    """
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path=f"/{db}"))


def _make_client(db: int) -> Redis:
    """Create a new async Valkey client pinned to ``db``."""
    url = _build_url_for_db(settings.VALKEY_URL, db)
    return redis.from_url(url, decode_responses=True)


async def get_valkey_otp() -> Redis:
    """DB 0 — sliding-window rate limits, plan-guard counters, refresh
    allowlist, AND the SHARED (un-prefixed) ai_ops budget brake.

    Lazy module-level singleton.  Reuses the same pool across calls.
    """
    global _otp_client
    if _otp_client is None:
        _otp_client = _make_client(0)
    return _otp_client


async def get_valkey_cache() -> Redis:
    """DB 3 — application read-through cache.  Consumed by ``core/cache.py``
    only.  Cache keys carry the ``category:`` §2.E prefix, applied in
    ``core/cache.py``'s ``_versioned_key`` (NOT here)."""
    global _cache_client
    if _cache_client is None:
        _cache_client = _make_client(3)
    return _cache_client


# ── Lua script registration (vendored verbatim — refresh allowlist) ─────────
async def load_lua_script(client: Redis, source: str) -> str:
    """Register ``source`` via ``SCRIPT LOAD``; return the SHA1 digest."""
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
    """Invoke a previously-loaded Lua script via ``EVALSHA``; fall back to
    ``EVAL`` on ``NOSCRIPT`` (Valkey restart flushed the script cache)."""
    keys = keys or []
    args = args or []
    try:
        return await client.evalsha(digest, len(keys), *keys, *args)
    except NoScriptError:
        logger.warning("EVALSHA NOSCRIPT — falling back to EVAL (digest=%s)", digest)
        return await client.eval(source, len(keys), *keys, *args)


async def aclose_all() -> None:
    """Close every cached client.  Called from the app-shutdown handler.

    Safe to call when some/all clients have not been initialised.
    """
    global _otp_client, _cache_client
    for name, client in (("otp", _otp_client), ("cache", _cache_client)):
        if client is not None:
            try:
                await client.aclose()
            except Exception as exc:  # pragma: no cover — best-effort teardown
                logger.warning("Valkey %s client aclose failed: %s", name, exc)
    _otp_client = None
    _cache_client = None


__all__ = [
    "get_valkey_otp",
    "get_valkey_cache",
    "load_lua_script",
    "eval_lua_script",
    "aclose_all",
]
