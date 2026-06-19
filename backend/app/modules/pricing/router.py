"""``pricing`` router — 1 endpoint handler per §12.B (LOCKED 2026-06-05) as
superseded by the **W2 Price Calculator rework (census-confirmed settlement
model, 2026-06-19)**.

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
``pricing.calculated`` on 2xx with payload
``{product_id, selling_price, estimated_bank_settlement}`` — no margin/
input_cost (those fields no longer exist in W2).  No PII per MVP_ARCH §11.9.

Rate-limit decorators (§4.G + §12.I)
------------------------------------
* POST ``/products/{id}/price-calc`` — 600/h per-IP (lightweight
  stateless math; per-user limit would degrade typing-rapid-iteration
  UX as sellers tweak ``selling_price`` to converge on a target settlement).

Plan-guard
----------
NOT participating (§12.I + §4.E) — pricing is one of the 3 V1 modules
excluded from plan_guard alongside ``customer`` (§8) and ``dashboard``
(§13).

Error mapping (W2 addition)
---------------------------
``pricing_lookup.UnknownCategoryError`` → ``CategoryPricingUnavailableError``
→ HTTP 422 ``pricing.category.no_pricing_data``.  A seeded category with no
pricing row is a data-integrity 4xx, NOT a 500.  The §4.F MeesellError handler
emits the locked envelope.
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.middleware.audit_mw import audit_event
from app.core.middleware.rate_limit_mw import rate_limit
from app.modules.pricing import service as pricing_service
from app.modules.pricing.exceptions import CategoryPricingUnavailableError
from app.modules.pricing.pricing_lookup import UnknownCategoryError
from app.modules.pricing.schemas import ApplyPriceRequest, PriceCalcRequest, PriceCalcResponse
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
    status_code=status.HTTP_200_OK,
    summary="Price Calculator (Feature 7) — census-confirmed bank-settlement estimate",
)
@rate_limit(scope="price_calc", limit=600, window=3600)
@audit_event("pricing.calculated")
async def price_calc(
    id: UUID,
    payload: PriceCalcRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PriceCalcResponse:
    """§12.B.1 — POST /products/{id}/price-calc (census-confirmed settlement
    estimator, W2).

    The seller supplies a ``selling_price``; the backend resolves the
    per-category shipping charge from the static lookup, applies the census-
    confirmed formula, and returns the estimated bank settlement.

    Status codes:
      * 200 — calc completed successfully.  A negative
        ``estimated_bank_settlement`` is ALSO a 200 — it carries a
        ``NEGATIVE_SETTLEMENT`` alert (NOT a 400).
      * 401 — JWT missing/invalid (handled by §4.A auth middleware).
      * 404 — ``catalog.product.not_found`` from the §10.C
        ``assert_product_ownership`` cross-module ownership gate.
      * 422 — ``pricing.category.no_pricing_data``: the product's
        ``meesho_leaf_id`` is absent from the pricing lookup (data-integrity
        gap); NOT a 500.
      * 422 — Pydantic body validation failure (``selling_price <= 0``,
        unknown extra fields, etc.).
    """
    # ── Feature flag guard (§3.2 / D2) ───────────────────────────────────
    if not settings.FEATURE_PRICE_CALCULATOR_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price Calculator is disabled in this environment",
        )

    # ── Service call — UnknownCategoryError → clean 422 (W2 addition) ────
    try:
        return await pricing_service.calculate(user.user_id, id, payload, db=db)
    except UnknownCategoryError as exc:
        # A seeded category with no pricing row is a data-integrity 4xx,
        # NOT a 500.  Map to the locked 422 MeesellError envelope so
        # _meesell_error_handler emits code="pricing.category.no_pricing_data".
        logger.warning(
            "pricing lookup miss for product_id=%s: %s",
            id,
            exc,
        )
        raise CategoryPricingUnavailableError(
            meesho_leaf_id=str(exc.args[0]) if exc.args else None,
            detail=str(exc.args[0]) if exc.args else None,
        ) from exc


# ─────────────────────────────────────────────────────────────────────────────
# 2. POST /products/{id}/apply-price — W4b explicit "Use this price" action
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/products/{id}/apply-price",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    summary=(
        "Apply calculated selling price to product (W4) — "
        "writes meesho_price into fields_jsonb for XLSX export"
    ),
)
@rate_limit(scope="price_apply", limit=60, window=3600)
@audit_event("pricing.price_applied")
async def apply_price(
    id: UUID,
    payload: ApplyPriceRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """W4b — POST /products/{id}/apply-price (explicit "Use this price" action).

    The calculator is an exploration tool; the product's ``fields_jsonb`` is
    mutated ONLY on this explicit seller action — NEVER silently on
    ``price-calc`` (founder ruling G-W4-APPLY Option A).

    Writes ``payload.selling_price`` into
    ``products.fields_jsonb["meesho_price"]`` via the existing
    ``catalog.service.patch_product`` write seam.  The export pipeline already
    emits any canonical present in ``fields_jsonb`` under its
    ``meesho_column_header`` — so this is the single link that makes the
    calculator's chosen price reach the XLSX.

    Status codes:
      * 204 — price written; no body.
      * 400 — ``validation.price.invalid_input``: selling_price ≤ 0
        (Pydantic also catches this at the route boundary).
      * 401 — JWT missing/invalid (auth middleware).
      * 404 — product not found / not owned (catalog ownership gate).
      * 422 — Pydantic body validation failure (e.g. selling_price missing
        or extra forbidden field from stale frontend).
    """
    if not settings.FEATURE_PRICE_CALCULATOR_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price Calculator is disabled in this environment",
        )

    await pricing_service.apply_price_to_product(
        user.user_id,
        id,
        payload.selling_price,
        db=db,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
