"""Plan-guard middleware — NO-OP for svc-pricing.

Vendored verbatim from the monolith ``app.core.middleware.plan_guard_mw`` (§4.G).
pricing is plan_guard-excluded (§0.9 / §12.I, alongside customer + dashboard),
so this middleware RUNS but passes through unconditionally.  Kept in the chain
so the §4.H 6-middleware shape is preserved across services.  Cannot fail.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class PlanGuardMiddleware(BaseHTTPMiddleware):
    """No-op pass-through for svc-pricing (pricing gates no plan resource)."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        return await call_next(request)


__all__ = ["PlanGuardMiddleware"]
