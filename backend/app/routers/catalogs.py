"""Catalog CRUD endpoints."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.catalog import Catalog
from app.models.image import Image
from app.models.sku import SKU
from app.models.user import User
from app.schemas.catalog import (
    CatalogCreate,
    CatalogDetailResponse,
    CatalogListResponse,
    CatalogResponse,
    CatalogStatus,
    CatalogUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/catalogs", tags=["catalogs"])


async def _load_owned_catalog(
    db: AsyncSession,
    catalog_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    with_skus: bool = False,
    include_deleted: bool = False,
) -> Catalog:
    stmt = select(Catalog).where(Catalog.id == catalog_id)
    if with_skus:
        stmt = stmt.options(selectinload(Catalog.skus).selectinload(SKU.images))
    catalog = (await db.execute(stmt)).scalar_one_or_none()
    if catalog is None or (catalog.status == "deleted" and not include_deleted):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog not found")
    if catalog.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return catalog


@router.post("", response_model=CatalogResponse, status_code=status.HTTP_201_CREATED)
async def create_catalog(
    data: CatalogCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CatalogResponse:
    catalog = Catalog(
        user_id=user.id,
        name=data.name,
        category=data.category,
        subcategory=data.subcategory,
        status="draft",
    )
    db.add(catalog)
    await db.commit()
    await db.refresh(catalog)
    return CatalogResponse.model_validate(catalog)


@router.get("", response_model=CatalogListResponse)
async def list_catalogs(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Annotated[CatalogStatus | None, Query(alias="status")] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> CatalogListResponse:
    base = select(Catalog).where(Catalog.user_id == user.id)
    if status_filter is None:
        base = base.where(Catalog.status != "deleted")
    else:
        base = base.where(Catalog.status == status_filter)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        await db.execute(
            base.order_by(Catalog.created_at.desc()).limit(limit).offset((page - 1) * limit)
        )
    ).scalars().all()

    return CatalogListResponse(
        data=[CatalogResponse.model_validate(c) for c in rows],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{catalog_id}", response_model=CatalogDetailResponse)
async def get_catalog(
    catalog_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CatalogDetailResponse:
    catalog = await _load_owned_catalog(db, catalog_id, user.id, with_skus=True)
    return CatalogDetailResponse.model_validate(catalog)


@router.put("/{catalog_id}", response_model=CatalogResponse)
async def update_catalog(
    catalog_id: uuid.UUID,
    data: CatalogUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CatalogResponse:
    catalog = await _load_owned_catalog(db, catalog_id, user.id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(catalog, field, value)
    await db.commit()
    await db.refresh(catalog)
    return CatalogResponse.model_validate(catalog)


@router.delete("/{catalog_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_catalog(
    catalog_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    catalog = await _load_owned_catalog(db, catalog_id, user.id)
    catalog.status = "deleted"
    await db.commit()
