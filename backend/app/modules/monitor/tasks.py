"""``monitor`` Celery task — the category change monitor dedupe gate (Wave 2 Unit C).

Owned by ``meesell-services-builder``. Part of the category change monitor
feature (``feature/category-monitor``).

Synchronous task
----------------
``@shared_task`` (NOT ``async def``) because Celery's V1 runtime does not
support coroutines — the async gate orchestrator (:func:`monitor.service.run_dedupe_gate`)
runs inside via ``asyncio.run(...)``, exactly mirroring
``app.modules.image.tasks.image_precheck_task`` (§11.E).

This task takes NO per-user argument — the monitor is a platform-level
background job over GLOBAL ``categories`` / ``category_snapshots`` tables. It
is therefore deliberately NOT added to ``_TASKS_REQUIRING_USER_REVALIDATION``
in ``workers/celery_app.py`` (same posture as the Razorpay billing sweeps).

Wave boundary (HARD)
--------------------
The task runs gate → scrape → diff → STORE VERDICT, and STOPS. NO fan-out,
NO notification-table write, NO ``category_subscription`` read, NO catalog
flags — those are Wave 4. On a BLOCK verdict the gate logs WARNING and stops.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from celery import shared_task

from app.shared.config import settings

logger = logging.getLogger(__name__)


@shared_task(
    name="monitor.scrape_category",
    bind=True,
)
def scrape_category_task(self, category_id: str | UUID) -> dict:
    """Celery wrapper for the category change monitor dedupe gate.

    Synchronous Celery task; the async gate runs inside via ``asyncio.run``.
    Returns the gate result dict (``action`` + verdict payload) so callers /
    monitors can read it from the Celery result backend (Valkey DB 2).

    Args:
        category_id: ``categories.id`` UUID (or its string form — Celery's
            JSON serialiser strips the UUID type).

    Returns:
        The :func:`monitor.service.run_dedupe_gate` result dict — one of
        ``{action: "ttl_reuse" | "coalesced" | "scraped", ...}``.

    Raises:
        CategoryNotFoundError: unknown category id (the gate clears its
            in-flight Valkey claim first).
        Exception: any live-scrape / diff failure propagates (in-flight
            claim cleared by the gate's ``finally`` first).
    """
    # Lazy import — keep module-level boot light (mirrors image/tasks.py).
    from app.modules.monitor.service import run_dedupe_gate

    cat_uuid = category_id if isinstance(category_id, UUID) else UUID(str(category_id))

    return asyncio.run(
        run_dedupe_gate(cat_uuid, db_url=settings.DATABASE_URL)
    )


__all__ = [
    "scrape_category_task",
]
