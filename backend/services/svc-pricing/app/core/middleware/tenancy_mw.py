"""Tenancy context middleware — pure-copy ``user_id`` injection.

Vendored verbatim from the monolith ``app.core.middleware.tenancy_mw`` (§4.G).
Copies ``request.state.user.user_id`` into ``request.state.user_id`` so
downstream layers (rate_limit_mw, audit_mw) read it without the getattr dance.
No enforcement here.  Cannot fail.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class TenancyContextMiddleware(BaseHTTPMiddleware):
    """Copy ``request.state.user.user_id`` into ``request.state.user_id``."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        user = getattr(request.state, "user", None)
        request.state.user_id = getattr(user, "user_id", None) if user is not None else None
        return await call_next(request)


__all__ = ["TenancyContextMiddleware"]
