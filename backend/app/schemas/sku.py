"""SKU request and response schemas."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.image import ImageResponse


class SKUCreate(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=255)
    cost_price: Decimal | None = None
    selling_price: Decimal | None = None
    weight_grams: int | None = None
    material: str | None = None
    sizes: str | None = None
    colors: str | None = None
    sort_order: int = 0


class SKUUpdate(BaseModel):
    product_name: str | None = None
    cost_price: Decimal | None = None
    selling_price: Decimal | None = None
    weight_grams: int | None = None
    material: str | None = None
    sizes: str | None = None
    colors: str | None = None
    ai_title: str | None = None
    ai_description: str | None = None
    ai_keywords: str | None = None
    ai_category: str | None = None
    ai_attributes: dict[str, Any] | None = None
    sort_order: int | None = None


class SKUResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    catalog_id: uuid.UUID
    product_name: str
    cost_price: Decimal | None = None
    selling_price: Decimal | None = None
    weight_grams: int | None = None
    material: str | None = None
    sizes: str | None = None
    colors: str | None = None
    ai_title: str | None = None
    ai_description: str | None = None
    ai_keywords: str | None = None
    ai_category: str | None = None
    ai_attributes: dict[str, Any] | None = None
    margin_amount: Decimal | None = None
    margin_percent: Decimal | None = None
    shipping_cost: Decimal | None = None
    return_provision: Decimal | None = None
    quality_score: int | None = None
    quality_checks: dict[str, Any] | None = None
    sort_order: int
    created_at: datetime
    images: list[ImageResponse] = []
