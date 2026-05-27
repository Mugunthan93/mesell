"""QualityGate validation endpoint."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.routers.catalogs import _load_owned_catalog
from app.schemas.quality import QualityReport
from app.services.quality_engine import QualityEngine

router = APIRouter(prefix="/api/v1/catalogs", tags=["quality"])


@router.post("/{catalog_id}/validate", response_model=QualityReport)
async def validate(
    catalog_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QualityReport:
    await _load_owned_catalog(db, catalog_id, user.id, with_skus=True)
    return await QualityEngine(db).validate_catalog(catalog_id)
