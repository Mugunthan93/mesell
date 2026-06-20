"""§18.B — Celery ``include=[...]`` MUST list exactly the 3 V1 task modules.

Per BACKEND_ARCHITECTURE.md §3.I canonical workers/ subtree and §18.B
V1 inventory (founder-ratified §3.I/§18.B canonical-inventory amendment
2026-06-19 for the Razorpay Wave 4 billing sweeps),
``celery_app.conf.include`` is locked to exactly three entries:

* ``app.modules.image.tasks``  — registers ``image.precheck`` (§11.E)
* ``app.modules.export.tasks`` — registers ``export.xlsx``  (§14.E)
* ``app.modules.iam.tasks``    — registers ``billing.reconcile`` +
                                 ``billing.trial_expiry_sweep`` (Razorpay
                                 Wave 4 beat tasks; FIRST beat_schedule
                                 in the repo)

The cardinality is a hard ceiling — adding a 4th task module beyond these
three is out-of-scope until a future founder-ratified inventory bump
(e.g. audit-events Celery sink per MVP_ARCH §14, or a quarterly
category-tree refresh task).

This test is the §18.B acceptance gate.  It also guards against
accidental V0-leftover re-additions (e.g. ``app.workers.generation_tasks``
was a V0 catalog-generation task module deleted in session 2; this test
+ the post-construction §3.I subtree check together ensure neither
sneaks back in).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.smoke


def test_include_list_is_exactly_3_v1_modules():
    """``celery_app.conf.include`` MUST equal the 3 V1 entries verbatim.

    Razorpay Wave 4 (2026-06-19) added ``app.modules.iam.tasks`` for the two
    periodic billing sweeps (``billing.reconcile`` + ``billing.trial_expiry_sweep``)
    per the founder-ratified §3.I/§18.B canonical-inventory amendment.
    """
    from app.workers.celery_app import celery_app

    assert celery_app.conf.include == [
        "app.modules.image.tasks",
        "app.modules.export.tasks",
        "app.modules.iam.tasks",
    ], (
        f"Expected exactly 3 V1 task modules in include list, "
        f"got: {celery_app.conf.include}"
    )


def test_include_list_does_not_carry_v0_modules():
    """V0 leftover modules (``app.workers.generation_tasks`` et al.) MUST
    NOT appear in the include list — §3.I + §18.B inventory."""
    from app.workers.celery_app import celery_app

    v0_forbidden = {
        "app.workers.generation_tasks",
        "app.workers.image_tasks",
        "app.workers.scrape_tasks",
        "app.modules.catalog.tasks",  # §10 has no tasks.py
        # NOTE: app.modules.iam.tasks was previously listed here as forbidden
        # (§7 had no tasks.py).  Razorpay Wave 4 (2026-06-19, founder-ratified
        # §3.I/§18.B amendment) introduced iam/tasks.py with the two billing
        # beat sweeps, so it is now a LEGITIMATE V1 module and was removed from
        # this forbidden set.  The other entries remain genuine V0 leftovers.
    }
    overlap = v0_forbidden & set(celery_app.conf.include)
    assert overlap == set(), f"V0-forbidden modules present: {overlap}"


def test_v1_tasks_discoverable_at_boot():
    """After ``loader.import_default_modules()``, the 2 V1 task names
    MUST appear in ``celery_app.tasks`` — §18 acceptance criterion 5."""
    from app.workers.celery_app import celery_app

    celery_app.loader.import_default_modules()

    assert "image.precheck" in celery_app.tasks, (
        "image.precheck task not discoverable — §11.E LOCKED task name"
    )
    assert "export.xlsx" in celery_app.tasks, (
        "export.xlsx task not discoverable — §14.E LOCKED task name "
        "(post-2026-06-08 amendment 18.A.1; was 'export.generate')"
    )


def test_only_v1_tasks_registered_at_module_level():
    """No 3rd-party V1 module sneaks a ``@celery_app.task`` registration
    via side-effect import (e.g. a re-introduced ``generation_tasks.py``
    importing ``celery_app`` and decorating with ``@celery_app.task``).

    The ``include=[...]`` list is the canonical loader; cross-checks
    that the registry size matches the inventory after default-module
    import.

    Razorpay Wave 4 (2026-06-19) added ``app.modules.iam.tasks`` which
    registers two billing beat tasks (``billing.reconcile`` +
    ``billing.trial_expiry_sweep``), so the expected user-task set is now
    four entries.  The set is still pinned exactly so an UNexpected task
    module is still caught.
    """
    from app.workers.celery_app import celery_app

    celery_app.loader.import_default_modules()

    user_tasks = {
        name
        for name in celery_app.tasks
        if not name.startswith("celery.")
    }
    assert user_tasks == {
        "image.precheck",
        "export.xlsx",
        "billing.reconcile",
        "billing.trial_expiry_sweep",
    }, (
        f"Expected exactly the 4 V1 user tasks, got: {sorted(user_tasks)}"
    )
