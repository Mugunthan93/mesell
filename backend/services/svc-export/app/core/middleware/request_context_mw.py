"""Request-context propagation middleware — feeds the extracted_clients shims.

Populates the per-request context-vars in
:mod:`app.core.extracted_clients._transport` so the 4 HTTP shims can forward
the caller's user JWT (``Authorization`` bearer) + correlation ID
(``X-Request-ID``) to the monolith ``/internal/*`` routes WITHOUT the
byte-for-byte-preserved ``service.py`` call sites having to thread them through.

Position
--------
Runs AFTER ``request_id`` (so ``request.state.request_id`` is set) and AFTER
``auth_mw`` (so a malformed header has already been screened) but the bearer
token is read straight from the raw ``Authorization`` header here — the shim
forwards the same opaque token the caller presented, unchanged.

This is svc-export-specific (the monolith has no such middleware — its export
module called the callees in-process with no header forwarding needed).  It is
NOT part of the §4.H 6-middleware chain count; it is an extraction-support
layer registered inside that chain.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.extracted_clients._transport import set_request_context


def _extract_bearer(request: Request) -> str | None:
    """Pull the opaque bearer token from the Authorization header (or None)."""
    auth_header = request.headers.get("Authorization") or request.headers.get(
        "authorization"
    )
    if not auth_header:
        return None
    parts = auth_header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Set the extracted_clients propagation context per request."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        set_request_context(
            bearer_token=_extract_bearer(request),
            request_id=getattr(request.state, "request_id", None),
        )
        return await call_next(request)


__all__ = ["RequestContextMiddleware"]
