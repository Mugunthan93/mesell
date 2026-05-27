"""Export endpoints: Meesho CSV + processed images ZIP."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.routers.catalogs import _load_owned_catalog
from app.services.export_service import generate_images_zip, generate_meesho_csv

router = APIRouter(prefix="/api/v1/catalogs", tags=["exports"])


@router.post("/{catalog_id}/export/meesho-csv")
async def export_csv(
    catalog_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    await _load_owned_catalog(db, catalog_id, user.id, with_skus=True)
    data, signed = await generate_meesho_csv(db, catalog_id)
    return {"download_url": signed, "size_bytes": len(data), "expiry_minutes": 60}


@router.post("/{catalog_id}/export/images-zip")
async def export_zip(
    catalog_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    await _load_owned_catalog(db, catalog_id, user.id, with_skus=True)
    data, signed = await generate_images_zip(db, catalog_id)
    return {"download_url": signed, "size_bytes": len(data), "expiry_minutes": 60}
