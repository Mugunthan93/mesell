"""Unit tests for the category change monitor Wave-3 trigger wiring.

The point of this unit is the V1-REGRESSION proof: hooks were inserted into
two LIVE seller flows — ``catalog.service.create_product`` (Feature 3) and the
``customer`` onboarding-complete path — and a Celery enqueue failure must NEVER
break either flow.

NON-LIVE CONTRACT (load-bearing)
--------------------------------
* The Celery task ``monitor.scrape_category`` / its ``.delay`` is MOCKED in
  EVERY test.  No test reaches a live broker, a live DB, or — transitively —
  live Meesho.  Grep this file's diff: there is ZERO ``*.meesho.com`` /
  ``async_playwright`` / ``webkit`` / ``.delay()`` against a real app.
* The host services are driven directly with mocked collaborators
  (repository + cross-module services + plan_guard) — no AsyncSession touches
  a real database.

Revert-check structure
----------------------
* Strip the ``enqueue_category_scrape(request.category_id)`` line in
  ``create_product`` → ``test_create_product_enqueues_once_with_leaf_category_id``
  goes RED (zero enqueues).
* Make ``enqueue_category_scrape`` re-raise (remove its ``try/except``) →
  ``test_create_product_succeeds_when_monitor_enqueue_raises`` +
  ``test_onboarding_complete_succeeds_when_monitor_enqueue_raises`` go RED
  (the host flow propagates the broker error).
* Drop the false→true edge guard → ``test_repeated_patch_on_complete_profile``
  goes RED (re-enqueue storm).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import app.modules.catalog.service as catalog_service
import app.modules.customer.service as customer_service
import app.modules.monitor.tasks as monitor_tasks

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _make_product_row(*, user_id, catalog_id, category_id, name):
    """A minimal duck-typed ProductORM row accepted by ``_orm_to_domain``."""
    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        catalog_id=catalog_id,
        category_id=category_id,
        name=name,
        status="draft",
        fields_jsonb={},
        ai_suggestions_jsonb={},
        created_at=None,
        updated_at=None,
        deleted_at=None,
    )


@pytest.fixture
def patched_create_product(monkeypatch):
    """Patch ``create_product``'s collaborators so it runs with no live DB.

    Returns the captured ``.delay`` mock (patched on the SOURCE task module)
    so each test can assert call counts / args.
    """
    user_id = uuid4()
    catalog_id = uuid4()
    category_id = uuid4()

    # plan_guard — no-op (cap not hit).
    monkeypatch.setattr(catalog_service, "enforce_plan_limit", AsyncMock(return_value=None))
    # category existence gate — passes.
    monkeypatch.setattr(
        catalog_service.category_service,
        "assert_category_exists",
        AsyncMock(return_value=None),
    )
    # eligibility gate — return None super_id so the customer call is skipped.
    monkeypatch.setattr(
        catalog_service,
        "_resolve_super_id_for_category",
        AsyncMock(return_value=None),
    )
    # repository — create catalog + insert product.
    catalog_obj = SimpleNamespace(id=catalog_id)
    row = _make_product_row(
        user_id=user_id, catalog_id=catalog_id, category_id=category_id, name="Tee"
    )
    monkeypatch.setattr(
        catalog_service.catalog_repo,
        "create_catalog",
        AsyncMock(return_value=catalog_obj),
    )
    monkeypatch.setattr(
        catalog_service.catalog_repo,
        "insert_product",
        AsyncMock(return_value=row),
    )

    delay = MagicMock()
    monkeypatch.setattr(monitor_tasks.scrape_category_task, "delay", delay)

    request = SimpleNamespace(category_id=category_id, catalog_id=None, name="Tee")
    return SimpleNamespace(
        user_id=user_id,
        category_id=category_id,
        request=request,
        delay=delay,
        insert_product=catalog_service.catalog_repo.insert_product,
    )


# ---------------------------------------------------------------------------
# Hook (a) — catalog-add
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_product_succeeds_when_monitor_enqueue_raises(
    patched_create_product, monkeypatch
):
    """A broker outage on enqueue MUST NOT break catalog-add."""
    ctx = patched_create_product
    # Make the enqueue blow up the way a dead broker would.
    ctx.delay.side_effect = RuntimeError("broker down")

    db = AsyncMock()
    product = await catalog_service.create_product(
        user_id=ctx.user_id, plan="free", request=ctx.request, db=db
    )

    # Product still returned + the row insert committed-as-far-as-the-service.
    assert product is not None
    assert product.category_id == ctx.category_id
    ctx.insert_product.assert_awaited_once()
    # The enqueue WAS attempted (and swallowed).
    ctx.delay.assert_called_once()


@pytest.mark.asyncio
async def test_create_product_enqueues_once_with_leaf_category_id(
    patched_create_product,
):
    """Exactly one enqueue, with ``str(request.category_id)`` (the LEAF id)."""
    ctx = patched_create_product

    db = AsyncMock()
    await catalog_service.create_product(
        user_id=ctx.user_id, plan="free", request=ctx.request, db=db
    )

    ctx.delay.assert_called_once_with(str(ctx.category_id))


# ---------------------------------------------------------------------------
# Hook (b) — onboarding-complete
# ---------------------------------------------------------------------------
def _profile_orm(*, onboarding_complete):
    """A duck-typed SellerProfileORM row for the customer service paths."""
    return SimpleNamespace(
        onboarding_complete=onboarding_complete,
        active_super_categories=[],
        compliance_extensions={},
        manufacturer_name="Acme",
        manufacturer_address="1 St",
        manufacturer_pincode="411001",
        packer_name="Acme",
        packer_address="1 St",
        packer_pincode="411001",
        country_of_origin="India",
        importer_name=None,
        importer_address=None,
        importer_pincode=None,
    )


@pytest.fixture
def patched_onboarding(monkeypatch):
    """Patch ``set_active_categories``'s collaborators (no live DB)."""
    user_id = uuid4()

    monkeypatch.setattr(
        customer_service, "_get_super_id_set", AsyncMock(return_value=set())
    )
    monkeypatch.setattr(
        customer_service, "_recompute_onboarding_complete", lambda *a, **k: True
    )
    monkeypatch.setattr(
        customer_service,
        "_invalidate_required_fields_cache",
        AsyncMock(return_value=None),
    )
    updated_row = _profile_orm(onboarding_complete=True)
    monkeypatch.setattr(
        customer_service.customer_repo,
        "update_active_categories",
        AsyncMock(return_value=updated_row),
    )
    # _orm_to_domain needs a full row; reuse the updated row's attrs.
    monkeypatch.setattr(
        customer_service, "_orm_to_domain", lambda row: SimpleNamespace(row=row)
    )

    leaf_a, leaf_b = uuid4(), uuid4()
    get_leaves = AsyncMock(return_value=[leaf_a, leaf_b])
    monkeypatch.setattr(
        customer_service.catalog_service,
        "get_distinct_product_category_ids",
        get_leaves,
    )

    delay = MagicMock()
    monkeypatch.setattr(monitor_tasks.scrape_category_task, "delay", delay)

    return SimpleNamespace(
        user_id=user_id,
        leaves=[leaf_a, leaf_b],
        get_leaves=get_leaves,
        delay=delay,
    )


@pytest.mark.asyncio
async def test_onboarding_complete_succeeds_when_monitor_enqueue_raises(
    patched_onboarding, monkeypatch
):
    """A broker outage on enqueue MUST NOT break onboarding-complete."""
    ctx = patched_onboarding
    # Profile was previously INCOMPLETE → this call crosses the false→true edge.
    monkeypatch.setattr(
        customer_service.customer_repo,
        "find_by_user_id",
        AsyncMock(return_value=_profile_orm(onboarding_complete=False)),
    )
    ctx.delay.side_effect = RuntimeError("broker down")

    db = AsyncMock()
    result = await customer_service.set_active_categories(
        user_id=ctx.user_id, super_ids=[], db=db
    )

    # The host flow still returns its profile, edge resolved + enqueue attempted.
    assert result is not None
    ctx.get_leaves.assert_awaited_once()
    assert ctx.delay.call_count == len(ctx.leaves)


@pytest.mark.asyncio
async def test_onboarding_transition_enqueues_per_distinct_leaf(
    patched_onboarding, monkeypatch
):
    """One enqueue per distinct product leaf on the false→true edge."""
    ctx = patched_onboarding
    monkeypatch.setattr(
        customer_service.customer_repo,
        "find_by_user_id",
        AsyncMock(return_value=_profile_orm(onboarding_complete=False)),
    )

    db = AsyncMock()
    await customer_service.set_active_categories(
        user_id=ctx.user_id, super_ids=[], db=db
    )

    assert ctx.delay.call_count == 2
    enqueued = {c.args[0] for c in ctx.delay.call_args_list}
    assert enqueued == {str(ctx.leaves[0]), str(ctx.leaves[1])}


@pytest.mark.asyncio
async def test_repeated_patch_on_complete_profile_does_not_reenqueue(
    patched_onboarding, monkeypatch
):
    """A re-PATCH of an ALREADY-complete profile must NOT re-enqueue."""
    ctx = patched_onboarding
    # Profile was ALREADY complete → no false→true edge this call.
    monkeypatch.setattr(
        customer_service.customer_repo,
        "find_by_user_id",
        AsyncMock(return_value=_profile_orm(onboarding_complete=True)),
    )

    db = AsyncMock()
    await customer_service.set_active_categories(
        user_id=ctx.user_id, super_ids=[], db=db
    )

    ctx.delay.assert_not_called()
    ctx.get_leaves.assert_not_awaited()
