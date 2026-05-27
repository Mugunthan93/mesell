"""SKU CRUD endpoints."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.catalog import Catalog
from app.models.sku import SKU
from app.models.user import User
from app.schemas.sku import SKUCreate, SKUResponse, SKUUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["skus"])


async def _load_owned_catalog(db, catalog_id, user_id) -> Catalog:
    catalog = await db.get(Catalog, catalog_id)
    if catalog is None or catalog.status == "deleted":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog not found")
    if catalog.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return catalog


async def _load_owned_sku(db: AsyncSession, sku_id: uuid.UUID, user_id: uuid.UUID) -> SKU:
    result = await db.execute(
        select(SKU)
        .join(Catalog)
        .where(SKU.id == sku_id, Catalog.user_id == user_id)
        .options(selectinload(SKU.images))
    )
    sku = result.scalar_one_or_none()
    if sku is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SKU not found")
    return sku


@router.post(
    "/catalogs/{catalog_id}/skus",
    response_model=SKUResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sku(
    catalog_id: uuid.UUID,
    data: SKUCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SKUResponse:
    await _load_owned_catalog(db, catalog_id, user.id)
    sku = SKU(catalog_id=catalog_id, **data.model_dump(exclude_unset=True))
    db.add(sku)
    await db.commit()
    await db.refresh(sku)
    sku.images = []
    return SKUResponse.model_validate(sku)


@router.put("/skus/{sku_id}", response_model=SKUResponse)
async def update_sku(
    sku_id: uuid.UUID,
    data: SKUUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SKUResponse:
    sku = await _load_owned_sku(db, sku_id, user.id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(sku, field, value)
    await db.commit()
    await db.refresh(sku)
    return SKUResponse.model_validate(sku)


@router.delete("/skus/{sku_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sku(
    sku_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    sku = await _load_owned_sku(db, sku_id, user.id)
    await db.delete(sku)
    await db.commit()
