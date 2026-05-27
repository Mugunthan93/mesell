"""Catalog request and response schemas."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.image import ImageResponse

CatalogStatus = Literal["draft", "generated", "validated", "exported", "deleted"]


class CatalogCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str | None = None
    subcategory: str | None = None


class CatalogUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = None
    subcategory: str | None = None
    status: CatalogStatus | None = None


class SKUSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_name: str
    cost_price: Decimal | None = None
    selling_price: Decimal | None = None
    quality_score: int | None = None
    sort_order: int
    images: list[ImageResponse] = []


class CatalogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    status: str
    category: str | None = None
    subcategory: str | None = None
    quality_score: int | None = None
    created_at: datetime
    updated_at: datetime


class CatalogDetailResponse(CatalogResponse):
    skus: list[SKUSummary] = []


class CatalogListResponse(BaseModel):
    data: list[CatalogResponse]
    total: int
    page: int
    limit: int
