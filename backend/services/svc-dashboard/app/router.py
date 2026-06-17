"""svc-dashboard router — 1 endpoint handler per §13.B (LOCKED 2026-06-05;
AMENDED 2026-06-07 §13.A.1).

Endpoints
---------
1. ``GET /api/v1/products``  — Paginated product listing (Feature 8)

Route invariants (§13.B + §4.B)
-------------------------------
* ``async def``.
* Requires ``Depends(get_current_user)`` — route does NOT decode JWT.
* Receives ``db: AsyncSession = Depends(get_db)`` and forwards as kwarg.
* NO business logic inlined — orchestration only.
* NO error-envelope formatting — exceptions raised are
  :class:`DashboardError` subclasses (V1: only ``InvalidPaginationError``)
  which ``core/errors.register_error_handlers`` (§4.F) translates into the
  locked envelope.

Audit posture (§13.B + §4.G)
----------------------------
NONE. Read-only endpoint per the §9 / §11 / §12 read-endpoint precedent.
``audit_mw`` skips writes on ``GET`` by default; dashboard inherits that
default without override.

Rate-limit decorators (§13.I + §4.E)
------------------------------------
* ``GET /products`` — 600/h (``dashboard_list`` scope). Same window as
  catalog's ``GET /products/{id}/preview`` and ``GET /products/{id}/draft``
  per §10.B precedent. Dashboard is polled on every page-navigation and
  on the refresh button — 10/min average is generous for normal sellers
  and absorbs occasional double-tab usage.

DECISION FLAG §13-DASHBOARD-D1
------------------------------
``rate_limit`` decorator has no ``key="ip"`` param; per-route keying is
automatic via ``request.state.user_id`` for authenticated routes (set by
``TenancyContextMiddleware``). §13.I locked spec calls for per-IP fallback
only, but the V1 decorator only supports per-user keying for authenticated
routes. Matches the catalog (§10 D2), customer (§8 D5), and iam (§7 D2)
precedent — keying lands as per-user; per-IP key form is a V1.5 decorator
enhancement. Per-user keying is the safer default anyway (one IP carrying
multiple sellers shares a higher limit naturally).

DECISION FLAG §13-DASHBOARD-D2
------------------------------
``GET /api/v1/products`` shares the path key ``/api/v1/products`` with
``POST /api/v1/products`` from §10 catalog. In the monolith FastAPI registers
them as two distinct ``APIRoute`` objects under one path key. In this
standalone service, svc-dashboard mounts only the GET — exactly 1 business
APIRoute object.

/internal/* routes
------------------
ZERO. dashboard is a leaf consumer (zero inbound callers) — svc-dashboard
exposes NO /internal/* routes of its own. The svc-dashboard OpenAPI contains
exactly 1 /api/v1 business route.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.middleware.rate_limit_mw import rate_limit
from app import service as dashboard_service
from app.schemas import DashboardQuery, DashboardResponse
from app.shared.config import settings
from app.shared.database import get_db

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/v1", tags=["dashboard"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. GET /products  — §13.B.1 (Feature 8)
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/products",
    response_model=DashboardResponse,
    summary="Paginated product listing (Feature 8 — Tracking Dashboard)",
)
@rate_limit(scope="dashboard_list", limit=600, window=3600)
async def list_products(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DashboardResponse:
    """§13.B.1 — GET /api/v1/products.

    Composes the seller's tracking-dashboard view by aggregating:

    * :func:`catalog.service.list_products` — paginated active products
      (most-recently-updated first per §10.D).
    * :func:`customer.service.get_onboarding_completeness` — profile
      completeness badge data.

    Empty inventory returns 200 with ``products=[]`` + ``total=0`` (NOT 404
    — empty inventory is a valid state for first-time sellers).

    Per §13.A.1 amendment (2026-06-07): ``status_filter`` and ``search``
    deferred to V1.5. V1 ships ``page`` + ``limit`` only.

    Status codes: 200, 400 (``validation.dashboard.invalid_pagination`` —
    raised by Pydantic ``Query`` validators on out-of-range inputs), 401.

    No audit event (read-only per §13.B + §4.G).
    No plan_guard (§13.I lock — dashboard is one of 3 plan_guard-excluded
    modules alongside customer + pricing).
    """
    # ── Feature flag guard (§3.2 / D3 kill-switch) ───────────────────────
    # D3 ruling: the read IS the feature — 404 on GET is intentional per
    # docs/plans/features/tracking-dashboard/FEATURE_PLAN.md §2.2.
    if not settings.FEATURE_TRACKING_DASHBOARD_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tracking Dashboard is disabled in this environment",
        )
    query = DashboardQuery(page=page, limit=limit)
    return await dashboard_service.list_products_for_dashboard(
        user_id=user.user_id,
        query=query,
        db=db,
    )


__all__ = ["router"]
