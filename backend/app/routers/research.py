"""Competitive-research endpoints (Meesho catalog scraping)."""

import logging
from typing import Annotated

import redis.asyncio as redis
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.middleware.rate_limit import enforce as enforce_rate_limit
from app.models.user import User
from app.routers.generation import _record_job, get_valkey
from app.schemas.scrape import ScrapeJobResponse, ScrapeRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["research"])


@router.post(
    "/research/scrape",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ScrapeJobResponse,
)
async def kickoff_scrape(
    payload: ScrapeRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    valkey: Annotated[redis.Redis, Depends(get_valkey)],
) -> ScrapeJobResponse:
    """Queue a Meesho scrape. Poll GET /api/v1/jobs/{job_id} for the result."""
    await enforce_rate_limit(valkey, user.id, "scrape")

    from app.workers.scrape_tasks import scrape_search
    async_result = scrape_search.delay(
        payload.url, payload.max_items, payload.endpoint_hint
    )
    job_id = str(async_result.id)
    await _record_job(
        valkey,
        job_id,
        {"type": "meesho_scrape", "url": payload.url, "status": "queued"},
    )
    return ScrapeJobResponse(job_id=job_id, status="queued", url=payload.url)
