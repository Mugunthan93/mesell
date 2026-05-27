"""Celery application factory."""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "meesell",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.image_tasks", "app.workers.generation_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.image_tasks.*": {"queue": "images"},
        "app.workers.generation_tasks.*": {"queue": "generation"},
    },
)
