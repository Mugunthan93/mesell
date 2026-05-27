"""Image upload, status, and deletion endpoints."""

import logging
import uuid
from typing import Annotated

import redis.asyncio as redis
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_current_user
from app.middleware.rate_limit import enforce as enforce_rate_limit
from app.models.catalog import Catalog
from app.models.image import Image
from app.models.sku import SKU
from app.models.user import User
from app.schemas.image import ImageResponse, ImageStatusResponse
from app.services.storage import get_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["images"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def _serialize(image: Image) -> ImageResponse:
    return ImageResponse(
        id=image.id,
        sku_id=image.sku_id,
        original_url=image.original_url,
        processed_url=image.processed_url,
        status="completed" if image.processed_url else "processing",
        width=image.width,
        height=image.height,
        bg_removed=image.bg_removed,
        resized=image.resized,
        has_watermark=image.has_watermark,
        is_compliant=image.is_compliant,
        sort_order=image.sort_order,
        created_at=image.created_at,
    )


async def _load_owned_sku(db: AsyncSession, sku_id: uuid.UUID, user_id: uuid.UUID) -> SKU:
    result = await db.execute(
        select(SKU).join(Catalog).where(SKU.id == sku_id, Catalog.user_id == user_id)
    )
    sku = result.scalar_one_or_none()
    if sku is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SKU not found")
    return sku


async def _load_owned_image(db: AsyncSession, image_id: uuid.UUID, user_id: uuid.UUID) -> Image:
    result = await db.execute(
        select(Image)
        .join(SKU)
        .join(Catalog)
        .where(Image.id == image_id, Catalog.user_id == user_id)
        .options(selectinload(Image.sku))
    )
    image = result.scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return image


@router.post(
    "/skus/{sku_id}/images",
    response_model=ImageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_image(
    sku_id: uuid.UUID,
    file: Annotated[UploadFile, File(...)],
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ImageResponse:
    await enforce_rate_limit(request.app.state.valkey, user.id, "images")
    sku = await _load_owned_sku(db, sku_id, user.id)

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type: {file.content_type}. Allowed: jpg, png",
        )

    body = await file.read()
    if len(body) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(body) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large ({len(body)} bytes, max {MAX_IMAGE_BYTES})",
        )

    ext = "png" if file.content_type == "image/png" else "jpg"
    image_id = uuid.uuid4()
    storage_path = f"originals/{user.id}/{image_id}.{ext}"
    url = await get_storage().upload(body, storage_path, content_type=file.content_type)

    image = Image(id=image_id, sku_id=sku.id, original_url=url, format=ext)
    db.add(image)
    await db.commit()
    await db.refresh(image)

    # Queue background processing (lazy import keeps the celery dep out of test paths).
    try:
        from app.workers.image_tasks import process_image

        process_image.delay(str(image.id))
    except Exception as exc:
        logger.warning(f"Failed to queue process_image for {image.id}: {exc}")

    return _serialize(image)


@router.get("/images/{image_id}/status", response_model=ImageStatusResponse)
async def image_status(
    image_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ImageStatusResponse:
    image = await _load_owned_image(db, image_id, user.id)
    return ImageStatusResponse(
        id=image.id,
        status="completed" if image.processed_url else "processing",
        processed_url=image.processed_url,
        width=image.width,
        height=image.height,
        is_compliant=image.is_compliant,
        has_watermark=image.has_watermark,
    )


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    image = await _load_owned_image(db, image_id, user.id)
    storage = get_storage()

    for url in (image.original_url, image.processed_url):
        if not url:
            continue
        try:
            await storage.delete(_storage_relative_path(url))
        except Exception as exc:
            logger.warning(f"Failed to delete storage object for {image.id}: {exc}")

    await db.delete(image)
    await db.commit()


def _storage_relative_path(url: str) -> str:
    """Strip transport/host so we get back e.g. ``originals/<user>/<image>.jpg``."""
    marker = "tmp/meesell/"
    if url.startswith("file://"):
        rest = url[len("file://") :].lstrip("/")
        idx = rest.find(marker)
        if idx >= 0:
            return rest[idx + len(marker) :]
        return rest
    if url.startswith("https://storage.googleapis.com/"):
        rest = url[len("https://storage.googleapis.com/") :]
        return rest.split("/", 1)[-1]
    return url
