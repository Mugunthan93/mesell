"""Generation kickoff and job-status endpoints."""

import json
import logging
import uuid
from typing import Annotated

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.catalog import Catalog
from app.models.user import User
from app.routers.catalogs import _load_owned_catalog
from app.routers.skus import _load_owned_sku

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["generation"])


def _job_key(job_id: str) -> str:
    return f"job:{job_id}"


async def _record_job(valkey: redis.Redis, job_id: str, payload: dict, ttl: int = 86400) -> None:
    await valkey.set(_job_key(job_id), json.dumps(payload), ex=ttl)


async def get_valkey(request: Request) -> redis.Redis:
    return request.app.state.valkey


@router.post("/catalogs/{catalog_id}/generate", status_code=status.HTTP_202_ACCEPTED)
async def kickoff_generation(
    catalog_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    valkey: Annotated[redis.Redis, Depends(get_valkey)],
) -> dict:
    catalog = await _load_owned_catalog(db, catalog_id, user.id)
    if (user.catalogs_used or 0) >= (user.catalogs_limit or 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Catalog generation limit reached for your plan; please upgrade.",
        )

    from app.workers.generation_tasks import generate_catalog
    async_result = generate_catalog.delay(str(catalog.id))
    job_id = str(async_result.id)
    await _record_job(
        valkey, job_id, {"type": "generate_catalog", "catalog_id": str(catalog.id), "status": "queued"}
    )
    return {"job_id": job_id, "status": "queued", "catalog_id": str(catalog.id)}


@router.post("/skus/{sku_id}/regenerate", status_code=status.HTTP_202_ACCEPTED)
async def regenerate(
    sku_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    valkey: Annotated[redis.Redis, Depends(get_valkey)],
    variation_index: int = 1,
) -> dict:
    sku = await _load_owned_sku(db, sku_id, user.id)
    from app.workers.generation_tasks import regenerate_sku
    async_result = regenerate_sku.delay(str(sku.id), variation_index)
    job_id = str(async_result.id)
    await _record_job(
        valkey,
        job_id,
        {"type": "regenerate_sku", "sku_id": str(sku.id), "variation": variation_index, "status": "queued"},
    )
    return {"job_id": job_id, "status": "queued", "sku_id": str(sku.id)}


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    user: Annotated[User, Depends(get_current_user)],
    valkey: Annotated[redis.Redis, Depends(get_valkey)],
) -> dict:
    raw = await valkey.get(_job_key(job_id))
    if raw is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    data = json.loads(raw)

    # Pull live state from Celery if available.
    try:
        from celery.result import AsyncResult

        from app.workers.celery_app import celery_app
        res = AsyncResult(job_id, app=celery_app)
        data["status"] = res.state.lower()
        if res.successful():
            data["result"] = res.result
        elif res.failed():
            data["error"] = str(res.result)
    except Exception:
        pass
    return data
