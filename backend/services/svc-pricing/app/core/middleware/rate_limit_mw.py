"""Sliding-window rate-limit middleware (Valkey DB 0).

Vendored from the monolith ``app.core.middleware.rate_limit_mw`` (§4.G + §4.H).

* Per-IP DDoS — unconditional sliding window of ``settings.RL_PER_IP_PER_MINUTE``
  requests/min keyed by ``request.client.host``.
* Per-route — only when the handler is decorated with :func:`rate_limit`.  The
  pricing ``POST /api/v1/products/{id}/price-calc`` carries
  ``@rate_limit(scope="price_calc", limit=600, window=3600)`` per-IP (router.py:74).
* Fail-open with WARNING on Valkey errors.

Keys are namespaced ``meesell:rl:*`` (unchanged from the monolith — the
sliding-window keyspace is DB 0).
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Match
from starlette.types import ASGIApp

from app.core.errors import MeesellError
from app.shared.config import settings
from app.shared.valkey import get_valkey_otp

logger = logging.getLogger(__name__)


# ── Typed error ────────────────────────────────────────────────────────────
class RateLimitExceededError(MeesellError):
    """Raised when the sliding window is full."""

    code = "rate_limit.exceeded"
    status_code = 429
    validation_message_id = "rate_limit.exceeded"


# ── Per-route decorator ────────────────────────────────────────────────────
def rate_limit(scope: str, limit: int, window: int) -> Callable:
    """Attach a ``__rate_limit__`` tag to a route handler."""

    def deco(fn: Callable) -> Callable:
        fn.__rate_limit__ = (scope, limit, window)  # type: ignore[attr-defined]
        return fn

    return deco


# ── Sliding-window counter ─────────────────────────────────────────────────
async def _check_window(key: str, limit: int, window: int) -> bool:
    """Return True if within budget; reserve a slot (ZADD) before returning True."""
    client = await get_valkey_otp()
    now = time.time()
    cutoff = now - window
    async with client.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(key, 0, cutoff)
        pipe.zcard(key)
        results = await pipe.execute()
    current = int(results[1])
    if current >= limit:
        return False
    member = f"{now}:{int(now * 1_000_000) % 1_000_000}"
    async with client.pipeline(transaction=True) as pipe:
        pipe.zadd(key, {member: now})
        pipe.expire(key, window)
        await pipe.execute()
    return True


# ── Envelope helper ────────────────────────────────────────────────────────
def _build_rate_limit_response(request: Request, detail: str) -> JSONResponse:
    """Return a 429 envelope identical to what the global error handler would.

    The exception path is not viable from inside ``BaseHTTPMiddleware`` because
    Starlette's exception middleware sits INNER to user-middleware — raising
    here bubbles past the ``MeesellError`` handler.  Build the envelope inline.
    """
    request_id = getattr(request.state, "request_id", None) or "unknown"
    body = {
        "detail": detail,
        "code": "rate_limit.exceeded",
        "validation_message_id": "rate_limit.exceeded",
        "request_id": request_id,
    }
    return JSONResponse(status_code=429, content=body)


# ── Middleware ─────────────────────────────────────────────────────────────
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce per-IP DDoS + per-route sliding windows.  Fails OPEN on Valkey error."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        client_ip = self._client_ip(request)

        # ── 1. Per-IP DDoS limit (unconditional) ──────────────────────────
        try:
            ok = await _check_window(
                key=f"meesell:rl:ip:{client_ip}:1m",
                limit=settings.RL_PER_IP_PER_MINUTE,
                window=60,
            )
        except (RedisError, ConnectionError, OSError) as exc:
            logger.warning(
                "rate_limit: Valkey unreachable for per-IP check (%s) — failing OPEN",
                exc,
            )
            ok = True
        if not ok:
            return _build_rate_limit_response(
                request,
                detail=(
                    f"Per-IP rate limit exceeded "
                    f"({settings.RL_PER_IP_PER_MINUTE}/min)."
                ),
            )

        # ── 2. Per-route limit (if decorated) ─────────────────────────────
        per_route = self._per_route_config(request)
        if per_route is not None:
            scope, limit, window = per_route
            user_id = getattr(request.state, "user_id", None)
            owner_part = (
                f"user:{user_id}" if user_id is not None else f"ip:{client_ip}"
            )
            key = f"meesell:rl:route:{scope}:{owner_part}:{window}"
            try:
                ok = await _check_window(key=key, limit=limit, window=window)
            except (RedisError, ConnectionError, OSError) as exc:
                logger.warning(
                    "rate_limit: Valkey unreachable for per-route check "
                    "(scope=%s, %s) — failing OPEN",
                    scope,
                    exc,
                )
                ok = True
            if not ok:
                return _build_rate_limit_response(
                    request,
                    detail=f"Rate limit exceeded for {scope} ({limit}/{window}s).",
                )

        return await call_next(request)

    @staticmethod
    def _client_ip(request: Request) -> str:
        """Best-effort client IP for keying (trusts ``X-Forwarded-For``)."""
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
        if request.client is not None:
            return request.client.host or "unknown"
        return "unknown"

    @staticmethod
    def _per_route_config(request: Request) -> tuple[str, int, int] | None:
        """Read the ``__rate_limit__`` tag off the would-be route handler.

        ``BaseHTTPMiddleware`` runs BEFORE Starlette populates
        ``request.scope["route"]``, so walk the app's routes and use
        ``route.matches(scope)`` to find the would-be match.
        """
        route = request.scope.get("route")
        endpoint = getattr(route, "endpoint", None)
        tag = getattr(endpoint, "__rate_limit__", None) if endpoint is not None else None
        if tag is not None:
            return tag

        app = request.scope.get("app")
        if app is None:
            return None
        try:
            routes = app.router.routes
        except AttributeError:  # pragma: no cover — defensive
            return None
        for r in routes:
            try:
                match, _ = r.matches(request.scope)
            except Exception:
                continue
            if match == Match.FULL:
                endpoint = getattr(r, "endpoint", None)
                if endpoint is not None:
                    tag = getattr(endpoint, "__rate_limit__", None)
                    if tag is not None:
                        return tag
                return None
        return None


__all__ = [
    "RateLimitMiddleware",
    "RateLimitExceededError",
    "rate_limit",
]
