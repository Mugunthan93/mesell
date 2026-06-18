"""``pricing`` router — 1 endpoint handler per §12.B (LOCKED 2026-06-05).

Endpoints
---------
1. ``POST /api/v1/products/{id}/price-calc`` — Price Calculator (Feature 7).

Route invariants (§12.B + §4.B)
-------------------------------
* Every handler is ``async def``.
* Every handler requires ``Depends(get_current_user)`` — routes NEVER
  decode JWT.
* Every handler receives ``db: AsyncSession = Depends(get_db)`` and
  forwards as kwarg.
* NO business logic inlined — orchestration only.
* NO error-envelope formatting — exceptions raised are ``PricingError``
  subclasses (or ``catalog.exceptions.ProductNotFoundError`` bubbled up
  from the cross-module ownership gate) which
  ``core/errors.register_error_handlers`` (§4.F) translates into the
  locked envelope.

Audit posture (§12.I + §4.G)
----------------------------
1 write endpoint gets an explicit ``@audit_event`` decorator emitting
``pricing.calculated`` on 2xx with payload ``{product_id, meesho_price,
input_cost, estimated_payout, margin_pct}``.  No PII per `MVP_ARCH §11.9`.

Rate-limit decorators (§4.G + §12.I)
------------------------------------
* POST ``/products/{id}/price-calc`` — 600/h per-IP (lightweight
  stateless math; per-user limit would degrade typing-rapid-iteration
  UX as sellers tweak ``meesho_price`` to converge on a target payout).

Plan-guard
----------
NOT participating (§12.I + §4.E) — pricing is one of the 3 V1 modules
excluded from plan_guard alongside ``customer`` (§8) and ``dashboard``
(§13).
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.middleware.audit_mw import audit_event
from app.core.middleware.rate_limit_mw import rate_limit
from app.modules.pricing import service as pricing_service
from app.modules.pricing.schemas import PriceCalcRequest, PriceCalcResponse
from app.shared.config import settings
from app.shared.database import get_db

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/v1", tags=["pricing"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. POST /products/{id}/price-calc — §12.B.1
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/products/{id}/price-calc",
    response_model=PriceCalcResponse,
    status_code=200,
    summary="Price Calculator (Feature 7) — deterministic P&L + alerts",
)
@rate_limit(scope="price_calc", limit=600, window=3600)
@audit_event("pricing.calculated")
async def price_calc(
    id: UUID,
    payload: PriceCalcRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PriceCalcResponse:
    """§12.B.1 — POST /products/{id}/price-calc (forward estimator, §12.M).

    Status codes:
      * 200 — calc completed successfully.  A negative estimated payout is
        ALSO a 200 — it carries a ``NEGATIVE_PAYOUT`` alert (§12.M (4)),
        NOT a 400.
      * 400 — ``validation.price.invalid_input`` (Pydantic catches
        ``meesho_price <= 0`` / ``input_cost <= 0`` / out-of-range
        percentages).
      * 401 — JWT missing/invalid (handled by §4.A auth middleware).
      * 404 — ``catalog.product.not_found`` from the §10.C
        ``assert_product_ownership`` cross-module ownership gate.

    Note (§12.M (4)): the legacy 422 ``pricing.commission.missing`` path
    is REMOVED — commission is now a seller-entered input (default 4%).
    """
    # ── Feature flag guard (§3.2 / D2) ───────────────────────────────────
    if not settings.FEATURE_PRICE_CALCULATOR_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price Calculator is disabled in this environment",
        )
    return await pricing_service.calculate(user.user_id, id, payload, db=db)


__all__ = ["router"]
