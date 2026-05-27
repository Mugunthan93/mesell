"""Celery tasks for image processing (T06).

The body runs synchronously inside the worker; it bridges to async services
via :func:`asyncio.run`. The task is queued by the upload endpoint (T05).
"""

import asyncio
import logging
import uuid

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="image.process", bind=True, max_retries=2)
def process_image(self, image_id: str) -> dict:
    """Run the full image pipeline: rembg → white BG → resize → upload → DB update."""
    from app.services.image_processor import run_pipeline

    try:
        return asyncio.run(run_pipeline(uuid.UUID(image_id)))
    except Exception as exc:
        logger.exception(f"process_image({image_id}) failed: {exc}")
        raise self.retry(exc=exc, countdown=10)
