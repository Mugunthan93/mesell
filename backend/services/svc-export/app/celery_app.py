"""svc-export Celery application — single-task worker (spec §3.A / §2.E).

Differences from the monolith ``app.workers.celery_app`` (which registered 2
task modules — image + export):

* SINGLE task module: ``include=["app.tasks"]`` (export.xlsx only).
* Dedicated queue ``svc-export`` (``task_default_queue``) so the export worker
  consumes from its own queue, isolated from any other service's broker traffic.
* Broker = Valkey DB 1, result backend = Valkey DB 2 (CLAUDE.md DB mapping,
  unchanged from the monolith).
* All Celery keys are NAMESPACED with ``svc-export:`` (§2.E) via
  ``broker_transport_options`` (broker keyspace) + ``result_backend_transport_options``
  (result keyspace), so svc-export's broker/result keys never collide with the
  monolith's or another service's in the shared Valkey instance.

Locked worker invariants (carried from the monolith §18.A/§18.G):
* ``task_serializer="json"`` / ``result_serializer="json"`` /
  ``accept_content=["json"]``.
* ``task_acks_late=True`` + ``task_reject_on_worker_lost=True`` (the export
  pipeline is row-level idempotent — re-execution overwrites partial state
  safely; per services-builder ALWAYS rules).
* ``worker_prefetch_multiplier=1`` (fairness over throughput).
* ``timezone="Asia/Kolkata"`` + ``enable_utc=True``.
* ``task_track_started=True`` (surfaces ``status="started"`` between enqueue
  and completion for the GET /exports/{id} poll).
"""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse

from celery import Celery

from app.shared.config import settings

# Celery key namespace prefix (§2.E) — every broker/result key carries this so
# svc-export never collides with the monolith or another service in Valkey.
_KEY_PREFIX = "svc-export:"
_QUEUE_NAME = "svc-export"


def _build_url_for_db(base_url: str, db: int) -> str:
    """Replace the database number path component in a redis:// URL.

    Mirrors :func:`app.shared.valkey._build_url_for_db`.  Celery expects URL
    strings at construction time, not Redis clients.
    """
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path=f"/{db}"))


BROKER_URL = _build_url_for_db(settings.VALKEY_URL, 1)
RESULT_BACKEND_URL = _build_url_for_db(settings.VALKEY_URL, 2)


celery_app = Celery(
    "svc-export",
    broker=BROKER_URL,
    backend=RESULT_BACKEND_URL,
    include=["app.tasks"],  # single task module — export.xlsx only
)

celery_app.conf.update(
    # Serialization (§18.A).
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Operational locks (§18.A).
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    # Reliability locks (§18.G + services-builder ALWAYS rules).
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # Dedicated queue — the export worker consumes from ``svc-export``.
    task_default_queue=_QUEUE_NAME,
    task_routes={"export.xlsx": {"queue": _QUEUE_NAME}},
    # §2.E key namespacing — prefix every broker + result key with ``svc-export:``.
    broker_transport_options={"global_keyprefix": _KEY_PREFIX},
    result_backend_transport_options={"global_keyprefix": _KEY_PREFIX},
)


__all__ = [
    "celery_app",
    "BROKER_URL",
    "RESULT_BACKEND_URL",
]
