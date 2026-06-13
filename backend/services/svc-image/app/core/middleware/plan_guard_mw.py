"""Plan-guard middleware — NO-OP for svc-image.

Vendored verbatim from the monolith ``app.core.middleware.plan_guard_mw`` (§4.G).
Image participates in no plan_guard resource (§11.J — the 4-slot uniform rule is
the structural DB-level limit), so this middleware RUNS but passes through
unconditionally.  Kept in the chain so the §4.H 6-middleware shape is preserved
across services.  Cannot fail.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class PlanGuardMiddleware(BaseHTTPMiddleware):
    """No-op pass-through for svc-image (image gates no plan resource — §11.J)."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        return await call_next(request)


__all__ = ["PlanGuardMiddleware"]
