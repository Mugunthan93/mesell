"""Celery application factory + V1 task registry + worker invariants.

This module is the single entrypoint for the Celery worker process and
the only authorised module in ``app/workers/`` alongside ``__init__.py``
per ``BACKEND_ARCHITECTURE.md §3.I`` canonical 2-file subtree.

What this file does
-------------------
1. Constructs the ``celery_app`` :class:`celery.Celery` instance.
2. Wires Valkey **DB 1** (broker) + **DB 2** (result backend) URLs from
   the V1 ``settings.VALKEY_URL`` via local ``_build_url_for_db`` —
   mirroring the helper in :mod:`app.shared.valkey` (Celery expects URL
   strings at construction time, not Redis clients).  See §18.E +
   ``CLAUDE.md`` Valkey DB mapping.
3. Registers the V1 task module include list (exactly 2 modules per
   §3.I + §18.B inventory — ``image`` + ``export``, no others).
4. Wires the :data:`task_prerun` signal handler that enforces §18.F
   worker JWT re-validation for the 2 V1 tasks WITHOUT modifying the
   LOCKED CONSTRUCTED ``image/tasks.py`` (§11.E) or ``export/tasks.py``
   (§14.E) bodies.

Locked worker invariants (do NOT remove)
----------------------------------------
* ``task_serializer="json"`` / ``result_serializer="json"`` /
  ``accept_content=["json"]`` — §18.A.
* ``task_acks_late=True`` — §18.G companion.
* ``task_reject_on_worker_lost=True`` — **session 2 G3 cleanup lock**
  recorded at §18.G; requeues a task when the worker dies mid-execution
  (image precheck + export pipeline are both row-level idempotent so
  re-execution overwrites partial state safely).
* ``worker_prefetch_multiplier=1`` — §18.A operational lock.  Fairness
  over throughput; image vs export task duration is heterogeneous and
  prefetching biases longer tasks under back-pressure.
* ``timezone="Asia/Kolkata"`` + ``enable_utc=True`` — §18.A operational.
* ``task_track_started=True`` — §18.A operational; enables the row 22 /
  row 26 poll endpoints to surface ``status="started"`` between enqueue
  and completion.

§18.F enforcement design (decision §18-CELERY-D2)
-------------------------------------------------
§18.F locks the pattern with ``_validate_user_or_abort`` living inside
each ``tasks.py``.  The §11.E + §14.E LOCKED CONSTRUCTED tasks.py files
do NOT include the call — adding it post-hoc would breach §5.0
NON-NEGOTIABLE.  Instead, this module installs a Celery ``task_prerun``
signal handler scoped to the 2 V1 task names.  The handler does a
synchronous existence check against the ``users`` table; on miss it
raises :class:`celery.exceptions.Reject` with ``requeue=False`` to
terminate the task without retry (user-deletion is a permanent
condition per §18.F).

V1 implementation note: the User model in
:mod:`app.shared.models.user` carries NO ``disabled`` or ``deleted_at``
columns — V1 has no soft-delete mechanism.  Validation reduces to an
existence check.  When V1.5 adds soft-delete columns, this handler
extends to ``WHERE id=$1 AND disabled=False AND deleted_at IS NULL``
without requiring a §18 amendment.
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


# ─────────────────────────────────────────────────────────────────────────────
# Valkey wiring — DB 1 broker, DB 2 result backend per §18.E + CLAUDE.md
# ─────────────────────────────────────────────────────────────────────────────
def _build_url_for_db(base_url: str, db: int) -> str:
    """Replace the database number path component in a redis:// URL.

    Mirrors :func:`app.shared.valkey._build_url_for_db` — duplicated
    here to avoid an import cycle between ``workers/`` and
    ``shared/valkey``.  Both helpers MUST behave identically;
    :func:`tests.test_celery_broker_db.test_broker_db_matches_helper`
    guards the contract.
    """
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path=f"/{db}"))


BROKER_URL = _build_url_for_db(settings.VALKEY_URL, 1)
RESULT_BACKEND_URL = _build_url_for_db(settings.VALKEY_URL, 2)


# ─────────────────────────────────────────────────────────────────────────────
# V1 Celery app — 2 task modules per §3.I + §18.B canonical inventory
# ─────────────────────────────────────────────────────────────────────────────
celery_app = Celery(
    "meesell",
    broker=BROKER_URL,
    backend=RESULT_BACKEND_URL,
    include=[
        "app.modules.image.tasks",   # image.precheck (§11.E LOCKED 2026-06-07)
        "app.modules.export.tasks",  # export.xlsx   (§14.E LOCKED 2026-06-08)
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    # SESSION 2 G3 CLEANUP LOCK — §18.G — DO NOT REMOVE.
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)


# ─────────────────────────────────────────────────────────────────────────────
# §18.F — worker JWT re-validation via task_prerun signal handler
# ─────────────────────────────────────────────────────────────────────────────
_TASKS_REQUIRING_USER_REVALIDATION = frozenset({
    "image.precheck",
    "export.xlsx",
})


def _extract_user_id_from_args(args: tuple, kwargs: dict) -> str | None:
    """Both V1 tasks accept ``(entity_id, user_id)`` positionally.

    Returns the ``user_id`` string if it can be found in args or kwargs,
    ``None`` otherwise.  A ``None`` return causes the prerun handler to
    no-op — a malformed call is the task body's responsibility to raise
    on.
    """
    user_id = kwargs.get("user_id") if kwargs else None
    if user_id is not None:
        return str(user_id)
    if args is not None and len(args) >= 2:
        return str(args[1])
    return None


async def _user_exists_async(user_id: UUID) -> bool:
    """Existence check against the ``users`` table via worker-safe session.

    Uses :func:`app.shared.database.make_worker_session` (NullPool) to
    avoid the prefork+asyncio.run cross-loop bug that ``AsyncSessionLocal``
    would hit when the prerun runs in a fresh event loop.
    """
    # Lazy imports keep module-level boot light + dodge the legacy
    # ``app.main`` import-chain that pulls in deleted V0 routers.
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

    Returns:
        * ``True``  — user row exists; task may proceed.
        * ``False`` — user row missing; task MUST be rejected per §18.F.

    On DB-side errors the wrapper logs WARNING and returns ``True``
    (fail-open) so that a transient outage does not block legitimate
    tasks.  Transient errors will be re-surfaced inside the task body
    via the normal repository layer.
    """
    try:
        user_uuid = UUID(user_id_str)
    except (TypeError, ValueError):
        # Malformed payload — treat as a hard failure so the task is
        # rejected rather than allowed to crash later with a less
        # informative error.
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
    """§18.F worker JWT re-validation enforcement.

    Filters to the 2 V1 tasks (``image.precheck``, ``export.xlsx``);
    raises :class:`celery.exceptions.Reject` with ``requeue=False`` on
    missing user.  Other tasks are unaffected.

    The signal handler runs in the worker's prefork-child main thread
    BEFORE the task body executes — see Celery docs ``task_prerun``.
    Raising ``Reject`` here aborts the task without retry and emits the
    standard Celery rejected-task log entry.
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
