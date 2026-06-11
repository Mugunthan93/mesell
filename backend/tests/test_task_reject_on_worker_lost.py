"""§18.G — ``task_reject_on_worker_lost=True`` MUST be preserved.

This setting is a **session 2 G3 cleanup lock** recorded in:
* ``BACKEND_ARCHITECTURE.md §18.G``  (final spec lock)
* ``.claude/agent-memory/meesell-services-builder/MEMORY.md`` — session
  2 final purge "Files MODIFIED" entry for ``workers/celery_app.py``.

Rationale: image precheck (§11.E) and export.xlsx (§14.E) are both
**row-level idempotent** — re-execution overwrites partial state safely.
Without ``task_reject_on_worker_lost=True``, a worker crash during
export step 7 (image ZIP packing) would leave the ``exports`` row in
an indeterminate state with partial GCS artefacts.  Requeueing on
worker-loss is the §18.G operational invariant that protects export
idempotency at scale.

Companion ``task_acks_late=True`` is also asserted — Celery requires
both to be set for worker-lost requeueing to take effect.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.smoke


def test_task_reject_on_worker_lost_is_true():
    """§18.G session-2-G3 lock — ``task_reject_on_worker_lost=True``."""
    from app.workers.celery_app import celery_app

    assert celery_app.conf.task_reject_on_worker_lost is True, (
        "task_reject_on_worker_lost MUST be True per §18.G "
        "(session 2 G3 cleanup lock — protects export idempotency on "
        "worker crash); got "
        f"{celery_app.conf.task_reject_on_worker_lost!r}"
    )


def test_task_acks_late_is_true():
    """Companion lock — task_acks_late=True is required for worker-lost
    requeueing to take effect.  §18.A + §18.G."""
    from app.workers.celery_app import celery_app

    assert celery_app.conf.task_acks_late is True, (
        "task_acks_late MUST be True per §18.A — companion to "
        f"task_reject_on_worker_lost; got {celery_app.conf.task_acks_late!r}"
    )


def test_worker_prefetch_multiplier_is_1():
    """§18.A operational lock — prefetch=1 keeps fairness over throughput
    when image and export tasks have heterogeneous durations."""
    from app.workers.celery_app import celery_app

    assert celery_app.conf.worker_prefetch_multiplier == 1, (
        "worker_prefetch_multiplier MUST equal 1 per §18.A operational "
        f"lock; got {celery_app.conf.worker_prefetch_multiplier!r}"
    )


def test_json_serialization_locked():
    """§18.A — JSON serialisation for tasks + results (no pickle, no yaml).

    Pickle is a well-documented Celery RCE vector; JSON is the V1 lock.
    """
    from app.workers.celery_app import celery_app

    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]


def test_timezone_is_asia_kolkata():
    """§18.A — timezone Asia/Kolkata + enable_utc=True for ops-visible
    timestamps that match the founder + Tirupur seller locality."""
    from app.workers.celery_app import celery_app

    assert celery_app.conf.timezone == "Asia/Kolkata"
    assert celery_app.conf.enable_utc is True
