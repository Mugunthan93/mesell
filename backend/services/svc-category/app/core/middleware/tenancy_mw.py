"""Tenancy context middleware — pure-copy ``user_id`` injection.

Per BACKEND_ARCHITECTURE.md §4.G:

* Position 4 in the chain (after ``auth_mw``).
* Reads ``request.state.user`` (set by ``auth_mw`` — may be None).
* Writes ``request.state.user_id`` — a UUID sentinel for log filters and
  for ``audit_mw`` to consume.
* **No enforcement here.**  401/403 is the dependency layer (``core/auth.py``)
  + the service layer (``core/tenancy.py``).  This middleware exists solely
  so downstream layers can read ``request.state.user_id`` without doing the
  ``getattr(request.state.user, "user_id", None)`` dance.

Failure mode: cannot fail — pure copy.
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
