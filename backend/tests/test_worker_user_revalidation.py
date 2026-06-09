"""§18.F — Worker JWT re-validation via ``task_prerun`` signal handler.

§18.F locks the rule: workers re-validate ``user_id`` against the
``users`` table before executing business logic.  Per dispatch
decision §18-CELERY-D2, the enforcement layer is the
``task_prerun`` signal handler in ``workers.celery_app`` (NOT a call
inserted into the LOCKED CONSTRUCTED §11.E ``image/tasks.py`` or
§14.E ``export/tasks.py``).

Acceptance contract for the handler:

1. Filter — only ``image.precheck`` and ``export.xlsx`` trigger the
   re-validation.  Other tasks (legitimately created in V1.5) MUST
   pass through untouched.
2. Missing user → ``Reject(requeue=False)``.  Terminates the task
   without retry (user-deletion is permanent per §18.F).
3. Existing user → no exception; task body proceeds.
4. Malformed ``user_id`` → ``Reject(requeue=False)``.
5. DB transient error → fail-OPEN (return True) so the legitimate task
   reaches the body, which then re-raises the DB error via the repo
   layer with task-level retry semantics.

V1 implementation note — the ``User`` model has NO ``disabled`` or
``deleted_at`` columns yet; validation reduces to a SELECT-by-id
existence check.  When V1.5 ships soft-delete columns, the handler
extends to ``WHERE id=$1 AND disabled=False AND deleted_at IS NULL``
without a §18 amendment.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from celery.exceptions import Reject


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def fake_image_task():
    """Mimics the @shared_task object Celery passes to the signal handler."""
    t = MagicMock()
    t.name = "image.precheck"
    return t


@pytest.fixture
def fake_export_task():
    t = MagicMock()
    t.name = "export.xlsx"
    return t


@pytest.fixture
def fake_other_task():
    """A V1.5 task that does NOT need user re-validation."""
    t = MagicMock()
    t.name = "audit.flush"   # hypothetical V1.5 task
    return t


@pytest.fixture
def user_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def entity_id() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — filter discipline: only the 2 V1 task names trigger the check
# ─────────────────────────────────────────────────────────────────────────────
def test_non_v1_task_is_not_revalidated(fake_other_task, entity_id, user_id):
    """V1.5 ``audit.flush`` task with a user_id arg MUST NOT trigger
    the existence check — the filter is a hard whitelist of the 2 V1
    task names per §18-CELERY-D2."""
    from app.workers.celery_app import _revalidate_user_pre_task

    with patch(
        "app.workers.celery_app._user_exists_sync", return_value=False
    ) as mock_exists:
        # Should NOT raise, even though _user_exists_sync would return False,
        # because the task name is not in the whitelist.
        _revalidate_user_pre_task(
            sender=fake_other_task,
            task_id="some-uuid",
            task=fake_other_task,
            args=(entity_id, user_id),
            kwargs={},
        )
        mock_exists.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — missing user → Reject(requeue=False) for image.precheck
# ─────────────────────────────────────────────────────────────────────────────
def test_missing_user_rejects_image_precheck_without_requeue(
    fake_image_task, entity_id, user_id
):
    """Soft-deleted user → ``Reject(requeue=False)`` for ``image.precheck``."""
    from app.workers.celery_app import _revalidate_user_pre_task

    with patch(
        "app.workers.celery_app._user_exists_sync", return_value=False
    ) as mock_exists:
        with pytest.raises(Reject) as exc_info:
            _revalidate_user_pre_task(
                sender=fake_image_task,
                task_id="some-uuid",
                task=fake_image_task,
                args=(entity_id, user_id),
                kwargs={},
            )

        # Reject MUST carry requeue=False (no retry — user-deletion is
        # permanent per §18.F).
        assert exc_info.value.requeue is False, (
            "Reject MUST be raised with requeue=False per §18.F — "
            "user-deletion is a permanent condition"
        )
        mock_exists.assert_called_once_with(user_id)


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — missing user → Reject(requeue=False) for export.xlsx too
# ─────────────────────────────────────────────────────────────────────────────
def test_missing_user_rejects_export_xlsx_without_requeue(
    fake_export_task, entity_id, user_id
):
    """Soft-deleted user → ``Reject(requeue=False)`` for ``export.xlsx``."""
    from app.workers.celery_app import _revalidate_user_pre_task

    with patch(
        "app.workers.celery_app._user_exists_sync", return_value=False
    ):
        with pytest.raises(Reject) as exc_info:
            _revalidate_user_pre_task(
                sender=fake_export_task,
                task_id="some-uuid",
                task=fake_export_task,
                args=(entity_id, user_id),
                kwargs={},
            )
        assert exc_info.value.requeue is False


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — existing user → no exception
# ─────────────────────────────────────────────────────────────────────────────
def test_existing_user_does_not_raise(fake_image_task, entity_id, user_id):
    """Active user → handler completes silently, task body proceeds."""
    from app.workers.celery_app import _revalidate_user_pre_task

    with patch(
        "app.workers.celery_app._user_exists_sync", return_value=True
    ) as mock_exists:
        # Must NOT raise.
        _revalidate_user_pre_task(
            sender=fake_image_task,
            task_id="some-uuid",
            task=fake_image_task,
            args=(entity_id, user_id),
            kwargs={},
        )
        mock_exists.assert_called_once_with(user_id)


# ─────────────────────────────────────────────────────────────────────────────
# Test 5 — keyword-style user_id arg also extracted
# ─────────────────────────────────────────────────────────────────────────────
def test_user_id_kwarg_extraction(fake_export_task, entity_id, user_id):
    """``user_id`` passed as kwarg (e.g. apply_async(kwargs={...}) path)
    MUST be extracted and re-validated."""
    from app.workers.celery_app import _revalidate_user_pre_task

    with patch(
        "app.workers.celery_app._user_exists_sync", return_value=False
    ) as mock_exists:
        with pytest.raises(Reject):
            _revalidate_user_pre_task(
                sender=fake_export_task,
                task_id="some-uuid",
                task=fake_export_task,
                args=(),
                kwargs={"export_id": entity_id, "user_id": user_id},
            )
        mock_exists.assert_called_once_with(user_id)


# ─────────────────────────────────────────────────────────────────────────────
# Test 6 — malformed user_id payload rejected
# ─────────────────────────────────────────────────────────────────────────────
def test_malformed_user_id_is_rejected(fake_image_task, entity_id):
    """A non-UUID ``user_id`` string MUST be treated as an unrecoverable
    payload and rejected (no retry) — matches §18.F semantics that the
    task body should not run if user identity cannot be confirmed."""
    from app.workers.celery_app import _user_exists_sync

    # Direct contract check on _user_exists_sync — malformed UUID → False.
    assert _user_exists_sync("not-a-uuid") is False


# ─────────────────────────────────────────────────────────────────────────────
# Test 7 — DB transient error fails OPEN (returns True)
# ─────────────────────────────────────────────────────────────────────────────
def test_db_error_fails_open(user_id):
    """A transient DB exception in ``_user_exists_async`` MUST be
    swallowed by ``_user_exists_sync`` returning True — the task body
    then re-attempts via its own repository layer, where Celery's
    autoretry semantics apply.  Fail-open is the §18.F observability
    rule."""
    from app.workers import celery_app as celery_app_mod

    async def _boom(_uid):
        raise RuntimeError("simulated DB outage")

    with patch.object(celery_app_mod, "_user_exists_async", side_effect=_boom):
        assert celery_app_mod._user_exists_sync(user_id) is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 8 — no user_id arg → no-op (no Reject)
# ─────────────────────────────────────────────────────────────────────────────
def test_no_user_id_is_noop(fake_image_task, entity_id):
    """A misconfigured ``args=(image_id,)`` call (missing user_id) MUST
    NOT trigger the existence check.  The task body owns the missing-arg
    failure mode — the prerun handler is conservative.
    """
    from app.workers.celery_app import _revalidate_user_pre_task

    with patch(
        "app.workers.celery_app._user_exists_sync", return_value=False
    ) as mock_exists:
        # No exception even though _user_exists_sync would say False —
        # because no user_id can be extracted.
        _revalidate_user_pre_task(
            sender=fake_image_task,
            task_id="some-uuid",
            task=fake_image_task,
            args=(entity_id,),
            kwargs={},
        )
        mock_exists.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Test 9 — whitelist cardinality (defensive — only 2 V1 entries)
# ─────────────────────────────────────────────────────────────────────────────
def test_revalidation_whitelist_is_exactly_two_v1_tasks():
    """The whitelist MUST equal {image.precheck, export.xlsx} verbatim.
    Adding a 3rd entry would silently expand §18.F enforcement to a
    task that hasn't been audited for the user_id positional contract."""
    from app.workers.celery_app import _TASKS_REQUIRING_USER_REVALIDATION

    assert _TASKS_REQUIRING_USER_REVALIDATION == frozenset({
        "image.precheck",
        "export.xlsx",
    }), (
        f"V1 whitelist MUST be exactly {{image.precheck, export.xlsx}}; "
        f"got {_TASKS_REQUIRING_USER_REVALIDATION}"
    )
