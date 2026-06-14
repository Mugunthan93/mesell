"""svc-iam async Valkey 8 client factories — DB-scoped, lazy-singleton.

Vendored from the monolith ``app.shared.valkey`` (BACKEND_ARCHITECTURE.md
§5.C), TRIMMED to the surface svc-iam actually consumes per SUB_PLAN_0G
§"Code surfaces":

* :func:`get_valkey_otp` (DB 0) — carries the OTP records (``otp:{phone}``),
  the FE-D5 refresh-allowlist (``cache:refresh:v{N}:{hmac}``), the per-IP /
  per-route rate-limit sliding windows, and the audit-coalesce markers.
* :func:`load_lua_script` / :func:`eval_lua_script` — the Lua registration +
  invocation helpers.  These are REQUIRED by the vendored ``core/auth.py``
  (auth-builder's file): the refresh-token rotation (``REFRESH_ROTATE_LUA``,
  GET→DEL→SET atomic) is loaded once via ``load_lua_script`` (cached SHA1) and
  invoked thereafter via ``eval_lua_script`` (EVALSHA → EVAL on NOSCRIPT).

iam runs NO Celery worker, so the broker (DB 1) and result-backend (DB 2)
factories from the monolith are NOT vendored.  iam is NOT a cache consumer —
the application read-through cache (DB 3) is also NOT vendored.

The factory boundary IS the DB-allocation enforcement (§1.B topology lock).
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
    """DB 0 — OTP records + FE-D5 refresh-allowlist + rate-limit windows.

    Lazy module-level singleton.  Reuses the same pool across calls.
    """
    global _otp_client
    if _otp_client is None:
        _otp_client = _make_client(0)
    return _otp_client


async def load_lua_script(client: Redis, source: str) -> str:
    """Register ``source`` with the server via ``SCRIPT LOAD``; return digest.

    Per §5.C, the canonical posture is: call this once at process startup,
    cache the returned SHA1 digest on the service singleton, and invoke
    thereafter via :func:`eval_lua_script` (which prefers ``EVALSHA``).

    Args:
        client: Any factory client (for iam the OTP-DB client — the
            refresh-token rotation Lua lives in DB 0).
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
    "load_lua_script",
    "eval_lua_script",
    "aclose_all",
]
