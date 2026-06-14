"""Opportunistic JWT-decode middleware — position 3 in the §4.H chain.

Vendored from the monolith ``app.core.middleware.auth_mw`` (§4.G).  Decodes the
``Authorization: Bearer <token>`` header (if present) and attaches the resulting
:class:`app.core.auth.CurrentUser` to ``request.state.user``.

Fail-open posture
-----------------
Missing / malformed / expired tokens leave ``request.state.user = None`` and the
request proceeds.  This middleware does NOT raise 401 — enforcement lives in
:func:`app.core.auth.get_current_user`.  Public routes (``/health``, ``/metrics``)
MUST traverse without a 401 short-circuit.

The HTTP metrics (``http_request_duration_seconds`` / ``http_requests_total``)
are observed here exactly once per request via ``_timed_call_next``.
"""

from __future__ import annotations

import logging
import time
from typing import Literal
from uuid import UUID

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.auth import CurrentUser
from app.core.metrics import HTTP_REQUEST_DURATION, HTTP_REQUESTS_TOTAL
from app.shared.config import settings

logger = logging.getLogger(__name__)


class AuthContextMiddleware(BaseHTTPMiddleware):
    """Opportunistically decode JWT and attach ``CurrentUser`` to request state.

    Fail-open — missing / malformed / expired tokens leave
    ``request.state.user = None``; the request proceeds normally.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.user = None

        async def _timed_call_next(req: Request) -> Response:
            start = time.perf_counter()
            response = await call_next(req)
            latency = time.perf_counter() - start
            route = req.scope.get("route")
            endpoint = getattr(route, "path", None) or req.url.path
            method = req.method
            status_code = str(response.status_code)
            HTTP_REQUEST_DURATION.labels(
                endpoint=endpoint, method=method, status_code=status_code
            ).observe(latency)
            HTTP_REQUESTS_TOTAL.labels(
                endpoint=endpoint, method=method, status_code=status_code
            ).inc()
            return response

        auth_header = request.headers.get("Authorization") or request.headers.get(
            "authorization"
        )
        if not auth_header:
            return await _timed_call_next(request)

        parts = auth_header.split(None, 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return await _timed_call_next(request)

        token = parts[1].strip()
        if not token:
            return await _timed_call_next(request)

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.InvalidTokenError:
            return await _timed_call_next(request)

        try:
            user_id = UUID(payload["sub"])
        except (KeyError, ValueError, TypeError):
            return await _timed_call_next(request)

        plan: Literal["free"] = "free"  # V1 narrow per §4.B
        request.state.user = CurrentUser(user_id=user_id, plan=plan)
        return await _timed_call_next(request)


__all__ = ["AuthContextMiddleware"]
