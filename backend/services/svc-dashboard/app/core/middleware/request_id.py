"""``X-Request-ID`` injection middleware (chain position 2, after CORS).

Vendored verbatim from the monolith ``app.core.middleware.request_id`` (§4.G).
Reads an incoming valid-UUID ``X-Request-ID`` (reused for correlation) or
generates a fresh ``uuid4``; writes ``request.state.request_id`` and echoes
the header on the response.  Cannot fail.
"""

from __future__ import annotations

import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

_HEADER_NAME = "X-Request-ID"


def _coerce_uuid(raw: str | None) -> str | None:
    """Return ``raw`` only when it parses as a UUID; else None."""
    if not raw:
        return None
    try:
        return str(uuid.UUID(raw))
    except (ValueError, AttributeError):
        return None


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Inject ``request.state.request_id`` + ``X-Request-ID`` response header."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        incoming = _coerce_uuid(request.headers.get(_HEADER_NAME))
        request_id = incoming or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[_HEADER_NAME] = request_id
        return response


__all__ = ["RequestIdMiddleware"]
