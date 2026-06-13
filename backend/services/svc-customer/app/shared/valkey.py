"""svc-customer async Valkey 8 client factories — DB-scoped, lazy-singleton.

Vendored from the monolith ``app.shared.valkey`` (BACKEND_ARCHITECTURE.md
§5.C), TRIMMED to the factories svc-customer actually consumes:

* :func:`get_valkey_otp`   (DB 0) — the per-IP / per-route rate-limit sliding
  windows + the audit-coalesce markers (vendored ``rate_limit_mw`` / ``audit_mw``).
* :func:`get_valkey_cache` (DB 3) — the read-through application cache (the 2
  customer cache contracts: ``customer.required_fields.{user_id}`` 60 s and
  ``customer.super_category_set`` 3600 s — §4.D + §8.B.5 + §8.I).

customer runs NO Celery worker, so the broker (DB 1) and result backend (DB 2)
factories from the monolith are NOT vendored.

The factory boundary IS the DB-allocation enforcement (§1.B topology lock).
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse, urlunparse

import redis.asyncio as redis
from redis.asyncio import Redis

from app.shared.config import settings

logger = logging.getLogger(__name__)

# ── Per-process lazy singletons ─────────────────────────────────────────────
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
    """DB 0 — sliding-window rate limits + audit-coalesce markers.

    Lazy module-level singleton.  Reuses the same pool across calls.
    """
    global _otp_client
    if _otp_client is None:
        _otp_client = _make_client(0)
    return _otp_client


async def get_valkey_cache() -> Redis:
    """DB 3 — read-through application cache (required_fields + super_category_set).

    Lazy module-level singleton.  Reuses the same pool across calls.
    """
    global _cache_client
    if _cache_client is None:
        _cache_client = _make_client(3)
    return _cache_client


async def aclose_all() -> None:
    """Close the cached clients.  Called from the app-shutdown handler.

    Safe to call when a client has not been initialised.
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
    "aclose_all",
]
