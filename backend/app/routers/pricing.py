"""Public PriceIntel endpoint (no auth) with authenticated enrichment."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_optional_user
from app.models.catalog import Catalog
from app.models.sku import SKU
from app.models.user import User
from app.schemas.pricing import PricingRequest, PricingResponse
from app.services.pricing_engine import calculate_pnl

router = APIRouter(prefix="/api/v1/pricing", tags=["pricing"])


@router.post("/calculate", response_model=PricingResponse)
async def calculate(
    data: PricingRequest,
    user: Annotated[User | None, Depends(get_optional_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> PricingResponse:
    return_rate = data.return_rate

    # Authenticated enrichment: use the user's empirical return rate for this category
    # (currently approximated by recomputing across their existing catalogs with
    # the same category, if any). For now we still fall back to the category default.
    if user is not None and return_rate is None and data.category and db is not None:
        result = await db.execute(
            select(func.count(SKU.id))
            .join(Catalog)
            .where(Catalog.user_id == user.id, Catalog.category == data.category)
        )
        # Placeholder for future per-user empirical lookup; no rate stored yet.
        _ = result.scalar_one()

    pnl = calculate_pnl(
        selling_price=data.selling_price,
        cost_price=data.cost_price,
        weight_grams=data.weight_grams,
        category=data.category,
        return_rate=return_rate,
        ad_spend=data.ad_spend,
        packaging=data.packaging,
        zone=data.zone,
    )
    return PricingResponse(**pnl, authenticated=user is not None)
