"""svc-image Celery application — single-task worker (spec §1 B1 / §0.4).

Differences from the monolith ``app.workers.celery_app`` (which registered 2
task modules — image + export) AND from svc-export's celery_app:

* SINGLE task module: ``include=["app.tasks"]`` (image.precheck only).
* Dedicated queue ``svc-image`` (``task_default_queue``) — NOT the monolith's
  ``image-tasks`` queue (that is monolith-only; PR #143), NOT the default
  queue.  The svc-image worker consumes from its own queue, isolated from any
  other service's broker traffic.
* Broker = Valkey DB 1, result backend = Valkey DB 2 (CLAUDE.md DB mapping).
* All Celery keys are NAMESPACED with ``svc-image:`` (§2.E) via
  ``broker_transport_options`` + ``result_backend_transport_options``, so
  svc-image's broker/result keys never collide with the monolith's or another
  service's in the shared Valkey instance.

NOTE — this is DISTINCT from the ai_ops budget brake keyspace
(``ai:cost:*`` on DB 0), which is INTENTIONALLY un-prefixed + SHARED across
services per §0.5/D6 (global ₹500/day cap).  The Celery key prefix here only
namespaces the BROKER (DB 1) + RESULTS (DB 2) keyspaces.

§18.F worker JWT re-validation (carried from the monolith — §1.G)
-----------------------------------------------------------------
The monolith ``celery_app`` installs a ``task_prerun`` signal handler that
re-validates the ``user_id`` exists in ``public.users`` before the task body
runs (the access JWT has expired by the time the task runs).  svc-image
CARRIES this handler scoped to ``image.precheck`` ONLY (per spec §1.G;
svc-export did NOT need it but image's spec requires it).  On a missing user
the handler raises ``celery.exceptions.Reject(requeue=False)`` — user deletion
is a permanent condition.

Locked worker invariants (carried from the monolith §18.A/§18.G):
* ``task_serializer``/``result_serializer``/``accept_content="json"``.
* ``task_acks_late=True`` + ``task_reject_on_worker_lost=True`` (the precheck
  pipeline is row-level idempotent — re-execution overwrites partial state
  safely; per services-builder ALWAYS rules).
* ``worker_prefetch_multiplier=1`` (fairness over throughput).
* ``timezone="Asia/Kolkata"`` + ``enable_utc=True``.
* ``task_track_started=True`` (surfaces ``status="started"`` between enqueue
  and completion for the GET /products/{id}/images poll).
"""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse, urlunparse
from uuid import UUID

from celery import Celery
from celery.exceptions import Reject
from celery.signals import task_prerun

from app.shared.config import settings

logger = logging.getLogger(__name__)

# Celery key namespace prefix (§2.E) — every broker/result key carries this so
# svc-image never collides with the monolith or another service in Valkey.
_KEY_PREFIX = "svc-image:"
_QUEUE_NAME = "svc-image"


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
    "svc-image",
    broker=BROKER_URL,
    backend=RESULT_BACKEND_URL,
    include=["app.tasks"],  # single task module — image.precheck only
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
    # Dedicated queue — the image worker consumes from ``svc-image``.
    task_default_queue=_QUEUE_NAME,
    task_routes={"image.precheck": {"queue": _QUEUE_NAME}},
    # §2.E key namespacing — prefix every broker + result key with ``svc-image:``.
    broker_transport_options={"global_keyprefix": _KEY_PREFIX},
    result_backend_transport_options={"global_keyprefix": _KEY_PREFIX},
)


# ─────────────────────────────────────────────────────────────────────────────
# §18.F — worker JWT re-validation via task_prerun signal handler (§1.G)
# ─────────────────────────────────────────────────────────────────────────────
_TASKS_REQUIRING_USER_REVALIDATION = frozenset({
    "image.precheck",
})


def _extract_user_id_from_args(args: tuple, kwargs: dict) -> str | None:
    """``image.precheck`` accepts ``(image_id, user_id)`` positionally.

    Returns the ``user_id`` string if it can be found in args or kwargs,
    ``None`` otherwise.  A ``None`` return causes the prerun handler to
    no-op — a malformed call is the task body's responsibility to raise on.
    """
    user_id = kwargs.get("user_id") if kwargs else None
    if user_id is not None:
        return str(user_id)
    if args is not None and len(args) >= 2:
        return str(args[1])
    return None


async def _user_exists_async(user_id: UUID) -> bool:
    """Existence check against ``public.users`` via a worker-safe session.

    Uses :func:`app.shared.database.make_worker_session` (NullPool) to avoid
    the prefork+asyncio.run cross-loop bug that ``AsyncSessionLocal`` would hit
    when the prerun runs in a fresh event loop.
    """
    from sqlalchemy import select

    from app.shared.database import make_worker_session
    from app.shared.models.user import User

    async with make_worker_session() as session:
        result = await session.execute(
            select(User.id).where(User.id == user_id).limit(1)
        )
        return result.scalar_one_or_none() is not None


def _user_exists_sync(user_id_str: str) -> bool:
    """Sync wrapper around :func:`_user_exists_async` for prerun context.

    Returns ``True`` if the user row exists (task may proceed), ``False`` if
    missing (task MUST be rejected per §18.F).  On DB errors, logs WARNING and
    returns ``True`` (fail-open) so a transient outage does not block
    legitimate tasks; the error re-surfaces inside the task body.
    """
    try:
        user_uuid = UUID(user_id_str)
    except (TypeError, ValueError):
        logger.error(
            "task_prerun: malformed user_id payload %r — rejecting",
            user_id_str,
        )
        return False

    try:
        return asyncio.run(_user_exists_async(user_uuid))
    except Exception as exc:  # noqa: BLE001 — defensive fail-open
        logger.warning(
            "task_prerun: user re-validation DB error (user=%s): %r",
            user_id_str,
            exc,
        )
        return True  # fail-open per §18.F observability rule


@task_prerun.connect
def _revalidate_user_pre_task(
    sender=None,
    task_id=None,
    task=None,
    args=None,
    kwargs=None,
    **_extra,
) -> None:
    """§18.F worker JWT re-validation enforcement (§1.G).

    Filters to ``image.precheck``; raises :class:`celery.exceptions.Reject`
    with ``requeue=False`` on a missing user.  Other tasks are unaffected.
    """
    task_name = getattr(task, "name", None) or getattr(sender, "name", None)
    if task_name not in _TASKS_REQUIRING_USER_REVALIDATION:
        return

    user_id_str = _extract_user_id_from_args(
        tuple(args or ()), dict(kwargs or {})
    )
    if user_id_str is None:
        # Task body will raise on missing positional arg — no-op here.
        return

    if not _user_exists_sync(user_id_str):
        logger.error(
            "task_prerun: rejected task=%s task_id=%s user=%s — user not "
            "found at worker pickup (per §18.F worker JWT re-validation)",
            task_name,
            task_id,
            user_id_str,
        )
        raise Reject(
            reason=f"user {user_id_str} not found at worker pickup",
            requeue=False,
        )


__all__ = [
    "celery_app",
    "BROKER_URL",
    "RESULT_BACKEND_URL",
]
