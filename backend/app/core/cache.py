"""Valkey DB 3 read-through cache + ETag helper + pre-warm hook.

Per BACKEND_ARCHITECTURE.md §4.D, this module owns the cache primitives
every read-through consumer uses: ``category`` (heaviest — schema + enum +
tree), ``customer`` (seller-profile read), ``catalog`` (schema read on
validate).

Key format (locked, MVP_ARCH §6.4)::

    meesell:v{cache_version}:{caller_key}

``cache_version`` lives in :mod:`app.shared.config` and bumps on the
quarterly Meesho corpus refresh — invalidates all schema/enum/category-tree
keys atomically without ``FLUSHDB``.

Stampede protection (MVP_ARCH §6.8)
-----------------------------------
``single_flight=True`` elects one fetcher via ``SET NX EX`` on a sibling
lock key; concurrent callers poll for the populated value.  Mandatory for
the 291 large Brand-pattern enum keys — simultaneous misses on a hot
category could each rebuild a ~200 KB JSON.

Pre-warm (MVP_ARCH §6.7) — DEFERRED CONTENT
-------------------------------------------
:func:`prewarm_top_categories` is wired from ``app/main.py`` startup but
ships as a **no-op stub** in V1 — actual category warming arrives with
§9's ``category`` module which owns the seed-list + fetch fn.  The stub
logs intent so we can grep the boot logs for confirmation.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Awaitable, Callable, TypeVar

from app.shared.config import settings
from app.shared.valkey import get_valkey_cache

logger = logging.getLogger(__name__)

T = TypeVar("T")

# ── Lock + polling constants ───────────────────────────────────────────────
_LOCK_TTL_SECONDS = 10           # short — fetch_fn is expected to finish fast
_POLL_INTERVAL_SECONDS = 0.05    # 50 ms
_POLL_MAX_WAIT_SECONDS = 5.0     # 5 s — at this point degrade and just fetch


def _versioned_key(key: str, version: str | None) -> str:
    """Build the locked ``meesell:v{cv}:{key}`` key."""
    cv = version if version is not None else settings.CACHE_VERSION
    return f"meesell:{cv}:{key}"


async def get_or_set(
    key: str,
    fetch_fn: Callable[[], Awaitable[T]],
    ttl: int,
    version: str | None = None,
    single_flight: bool = False,
) -> T:
    """Read-through Valkey cache primitive.

    On miss, calls ``fetch_fn()``, JSON-serialises the result, ``SET ex``
    in Valkey, and returns the value.  On hit, returns the cached value
    (JSON-deserialised) directly.

    Args:
        key: Logical key (the version prefix is added internally).
        fetch_fn: Async callable that returns the value on cache miss.
            Result MUST be JSON-serialisable.
        ttl: Seconds to keep the value in Valkey.  Required — every
            cache entry has a TTL.
        version: Override the global ``CACHE_VERSION``.  Defaults to
            ``settings.CACHE_VERSION``.
        single_flight: When True, use ``SET NX EX`` lock to elect a single
            fetcher; concurrent callers poll for the populated value.
            Mandatory for hot enum keys (MVP_ARCH §6.8).

    Returns:
        The cached or newly-fetched value.
    """
    full_key = _versioned_key(key, version)
    client = await get_valkey_cache()

    # Fast path: read existing value.
    cached = await client.get(full_key)
    if cached is not None:
        return json.loads(cached)

    if not single_flight:
        # Simple miss path — fetch, set, return.
        value = await fetch_fn()
        await client.set(full_key, json.dumps(value), ex=ttl)
        return value

    # ── Single-flight path ────────────────────────────────────────────────
    lock_key = f"{full_key}:lock"
    acquired = await client.set(lock_key, "1", nx=True, ex=_LOCK_TTL_SECONDS)

    if acquired:
        try:
            value = await fetch_fn()
            await client.set(full_key, json.dumps(value), ex=ttl)
            return value
        finally:
            # Best-effort lock release; TTL is the safety net.
            try:
                await client.delete(lock_key)
            except Exception as exc:  # pragma: no cover — best-effort
                logger.warning("cache lock release failed for %s: %s", lock_key, exc)

    # Lock NOT acquired — poll the value key for up to _POLL_MAX_WAIT_SECONDS.
    waited = 0.0
    while waited < _POLL_MAX_WAIT_SECONDS:
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        waited += _POLL_INTERVAL_SECONDS
        cached = await client.get(full_key)
        if cached is not None:
            return json.loads(cached)

    # Timed out waiting for the elected fetcher — degrade and fetch ourselves.
    # Do NOT set the lock; the original fetcher will set the value.
    logger.warning(
        "single-flight poll timed out for %s — falling back to direct fetch", full_key
    )
    value = await fetch_fn()
    # We still SET so subsequent callers hit warm cache, even though we
    # raced past the original elected fetcher.
    await client.set(full_key, json.dumps(value), ex=ttl)
    return value


def etag_for(payload: bytes) -> str:
    """Return a quoted strong ETag per RFC 7232.

    Format::

        "<64-hex-sha256>"

    Caller writes this into the ``ETag`` response header so Angular's
    ``HttpClient`` can short-circuit with 304 Not Modified on the next
    request (MVP_ARCH §6.6).
    """
    digest = hashlib.sha256(payload).hexdigest()
    return f'"{digest}"'


async def prewarm_top_categories(n: int = 100) -> None:
    """Pre-warm the hot category cache on FastAPI startup.

    V1 STUB — actual warming logic lives in §9's ``category`` module,
    which owns the seed-list of top categories + the schema fetch fn.
    Today this just logs intent so boot-time confirmation is greppable.

    Args:
        n: Number of categories to warm (default 100 per MVP_ARCH §6.7
            hot-tier strategy).  Forwarded to §9 once it lands.
    """
    logger.info("prewarm_top_categories(n=%d) — V1 no-op stub (§9 not yet built)", n)


__all__ = [
    "get_or_set",
    "etag_for",
    "prewarm_top_categories",
]
