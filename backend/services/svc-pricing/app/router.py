"""svc-pricing router — 1 endpoint handler (spec §3.B / §0.7 LOCKED 2026-06-05).

Endpoints
---------
1. ``POST /api/v1/products/{id}/price-calc`` — Price Calculator (Feature 7).

Route invariants (§12.B + §4.B)
--------------------------------
* Every handler is ``async def``.
* Every handler requires ``Depends(get_current_user)`` — routes NEVER
  decode JWT directly.
* Every handler receives ``db: AsyncSession = Depends(get_db)`` and
  forwards as kwarg.
* NO business logic inlined — orchestration only.
* NO ``/internal/*`` routes (pricing is a LEAF CONSUMER with zero inbound
  callers — spec §0.4).

Audit posture (§12.I + §4.G)
------------------------------
1 write endpoint gets an explicit ``@audit_event`` decorator emitting
``pricing.calculated`` on 2xx with payload ``{product_id, input_cost,
mrp, profit_pct}``.  No PII per ``MVP_ARCH §11.9``.

Rate-limit decorators (§4.G + §12.I)
--------------------------------------
* POST ``/products/{id}/price-calc`` — 600/h per-IP (lightweight
  stateless math; per-user limit would degrade typing-rapid-iteration
  UX as sellers tweak ``target_margin_pct`` to converge on a price).

Plan-guard
----------
NOT participating (§12.I + §4.E) — pricing is one of the 3 V1 modules
excluded from plan_guard alongside ``customer`` (§8) and ``dashboard``
(§13).

Frozen path-param (§0.7 verified — monolith router.py:69)
-----------------------------------------------------------
Path parameter is ``{id}`` NOT ``{product_id}`` — verbatim from the
monolith.  Any drift here is a hard reject (image session precedent).
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
from app import service as pricing_service
from app.schemas import PriceCalcRequest, PriceCalcResponse
from app.shared.config import settings
from app.shared.database import get_db

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/v1", tags=["pricing"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. POST /products/{id}/price-calc — §12.B.1 / spec §0.7
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
    """§12.B.1 — POST /products/{id}/price-calc.

    Status codes:
      * 200 — calc completed successfully.
      * 400 — ``validation.price.invalid_input`` (Pydantic catches
        ``input_cost <= 0`` / ``target_margin_pct < 0`` / etc.; service
        adds the V1.5 cross-field surface).
      * 401 — JWT missing/invalid (handled by §4.A auth middleware).
      * 404 — ``catalog.product.not_found`` from the §10.C
        ``assert_product_ownership`` cross-module ownership gate.
      * 422 — ``pricing.commission.missing`` when the resolved category
        has no usable commission rate.
    """
    # ── Feature flag guard (§3.2 / flag-parity) ──────────────────────────
    if not settings.FEATURE_PRICE_CALCULATOR_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price Calculator is disabled in this environment",
        )
    return await pricing_service.calculate(user.user_id, id, payload, db=db)


__all__ = ["router"]
