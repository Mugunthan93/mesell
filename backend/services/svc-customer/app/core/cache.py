"""Valkey DB 3 read-through cache + ETag helper.

Vendored from the monolith ``app.core.cache`` (BACKEND_ARCHITECTURE.md §4.D),
TRIMMED to the primitives svc-customer consumes — ``get_or_set`` (the customer
service's 2 cache contracts: ``customer.required_fields.{user_id}`` 60 s and
``customer.super_category_set`` 3600 s) + ``etag_for``.

``prewarm_top_categories`` is NOT vendored — it is a category-module concern
(it imports ``app.modules.category.service`` + ``make_worker_session``); customer
runs no startup prewarm and has no Celery worker session.

Key format (locked, MVP_ARCH §6.4)::

    meesell:v{cache_version}:{caller_key}

``cache_version`` lives in :mod:`app.shared.config` and bumps on the quarterly
Meesho corpus refresh — invalidates all keys atomically without ``FLUSHDB``.

Stampede protection (MVP_ARCH §6.8)
-----------------------------------
``single_flight=True`` elects one fetcher via ``SET NX EX`` on a sibling lock
key; concurrent callers poll for the populated value.  customer's
``super_category_set`` loader uses ``single_flight=True`` (global reference
read).
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

    On miss, calls ``fetch_fn()``, JSON-serialises the result, ``SET ex`` in
    Valkey, and returns the value.  On hit, returns the cached value
    (JSON-deserialised) directly.

    Args:
        key: Logical key (the version prefix is added internally).
        fetch_fn: Async callable that returns the value on cache miss.  Result
            MUST be JSON-serialisable.
        ttl: Seconds to keep the value in Valkey.  Required.
        version: Override the global ``CACHE_VERSION``.  Defaults to
            ``settings.CACHE_VERSION``.
        single_flight: When True, use ``SET NX EX`` lock to elect a single
            fetcher; concurrent callers poll for the populated value.

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
    logger.warning(
        "single-flight poll timed out for %s — falling back to direct fetch", full_key
    )
    value = await fetch_fn()
    await client.set(full_key, json.dumps(value), ex=ttl)
    return value


def etag_for(payload: bytes) -> str:
    """Return a quoted strong ETag per RFC 7232.

    Format::

        "<64-hex-sha256>"
    """
    digest = hashlib.sha256(payload).hexdigest()
    return f'"{digest}"'


__all__ = [
    "get_or_set",
    "etag_for",
]
