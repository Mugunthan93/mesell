"""Plan-guard middleware — **V1 NO-OP placeholder**.

Per BACKEND_ARCHITECTURE.md §4.G:

* Position 6 in the chain (after ``rate_limit_mw``, before the route).
* In V1 this middleware is **wired but inert** so V1.5 can light it without
  changing the middleware chain order or registration code.
* V1.5 will gate **global plan validity** here (e.g. subscription expired
  → 402 across every route).  Per-feature budget enforcement (the four
  resources in §4.E) stays in ``core/plan_guard.py``, which V1 callers
  invoke from the service layer at the write site.

Failure mode: cannot fail (no-op).
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class PlanGuardMiddleware(BaseHTTPMiddleware):
    """V1 no-op placeholder.  V1.5 lights up subscription-expiry gating."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        # V1.5 wiring point — read ``request.state.user.plan`` and raise
        # PlanLimitExceededError on global gates (e.g. expired subscription).
        return await call_next(request)


__all__ = ["PlanGuardMiddleware"]
