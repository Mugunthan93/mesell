"""Celery application factory.

V1 task modules will be re-introduced during construction phase
(image pre-check, export generation, etc.). The include list is intentionally
empty until those task modules are authored against the V1 13-table schema.
"""

from celery import Celery

from app.shared.config import settings

celery_app = Celery(
    "meesell",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)
