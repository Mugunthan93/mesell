"""svc-export async Valkey 8 client factories — DB-scoped, lazy-singleton.

Vendored from the monolith ``app.shared.valkey`` (BACKEND_ARCHITECTURE.md
§5.C), TRIMMED to the factories svc-export actually consumes:

* :func:`get_valkey_otp` (DB 0) — the cosmetic export-format hint key
  (``export:format:{export_id}``, 10-min TTL) + the per-IP / per-route
  rate-limit sliding windows.

The Celery broker (DB 1) and result backend (DB 2) URLs are wired directly
in ``app.celery_app`` via its own ``_build_url_for_db`` (Celery expects URL
strings, not Redis clients), so the broker/results factories from the
monolith are NOT vendored here.  The application read-through cache (DB 3)
is a category/catalog concern, not an export one — also not vendored.

The factory boundary IS the DB-allocation enforcement (§1.B topology lock).
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse, urlunparse

import redis.asyncio as redis
from redis.asyncio import Redis

from app.shared.config import settings

logger = logging.getLogger(__name__)

# ── Per-process lazy singleton ──────────────────────────────────────────────
_otp_client: Redis | None = None


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
    """DB 0 — export-format hint + sliding-window rate limits.

    Lazy module-level singleton.  Reuses the same pool across calls.
    """
    global _otp_client
    if _otp_client is None:
        _otp_client = _make_client(0)
    return _otp_client


async def aclose_all() -> None:
    """Close the cached client.  Called from the app-shutdown handler.

    Safe to call when the client has not been initialised.
    """
    global _otp_client
    if _otp_client is not None:
        try:
            await _otp_client.aclose()
        except Exception as exc:  # pragma: no cover — best-effort teardown
            logger.warning("Valkey otp client aclose failed: %s", exc)
    _otp_client = None


__all__ = [
    "get_valkey_otp",
    "aclose_all",
]
