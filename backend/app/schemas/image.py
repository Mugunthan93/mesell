"""Image-related Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ImageStatus = Literal["processing", "completed"]


class ImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku_id: uuid.UUID
    original_url: str
    processed_url: str | None = None
    status: ImageStatus = "processing"
    width: int | None = None
    height: int | None = None
    bg_removed: bool = False
    resized: bool = False
    has_watermark: bool = False
    is_compliant: bool = True
    sort_order: int = 0
    created_at: datetime


class ImageStatusResponse(BaseModel):
    id: uuid.UUID
    status: ImageStatus
    processed_url: str | None = None
    width: int | None = None
    height: int | None = None
    is_compliant: bool = True
    has_watermark: bool = False
