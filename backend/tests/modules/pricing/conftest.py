"""Pricing-module pytest fixtures.

Per BACKEND_ARCHITECTURE.md §12.J:

* ``user`` — a logged-in seller.
* ``other_user`` — a second seller (for the cross-tenant ownership-gate test).
* ``priced_category`` — a category seeded with ``commission_pct=15`` so the
  full ``pricing.service.calculate`` path completes without raising
  :class:`CommissionMissingError`.
* ``uncommissioned_category`` — a category with ``commission_pct=NULL``.
  Per §9.C, :func:`category.service.get_commission` returns
  ``Decimal("0.00")`` for this row — the §12-PRICING-D1 missing-signal.
* ``catalog_row`` — a catalog under ``user``.
* ``product_row`` — a product under ``user`` in ``catalog_row`` pointing at
  ``priced_category``.
* ``other_user_product`` — a product under ``other_user`` (cross-tenant
  fixture for the ownership-gate test).

The ``db`` fixture is the top-level conftest's ``db_session`` — fresh
ephemeral test DB (Postgres on :5432 via ``DATABASE_URL`` env in
``tests/conftest.py``).  The DB is reset per test (drop_all + create_all).
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest_asyncio

from datetime import datetime, timezone

from app.shared.models.catalog import Catalog as CatalogORM
from app.shared.models.category import Category as CategoryORM
from app.shared.models.product import Product as ProductORM
from app.shared.models.template import Template as TemplateORM
from app.shared.models.user import User


@pytest_asyncio.fixture(loop_scope="function")
async def db(db_session):
    """Alias for the ephemeral test DB session — matches the §8 / §10
    fixture-naming convention so the test signatures read naturally."""
    yield db_session


# ─────────────────────────────────────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_user(db, phone: str) -> User:
    user = User(phone=phone, plan="free")
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture(loop_scope="function")
async def user(db) -> User:
    return await _seed_user(db, phone="+915550012001")


@pytest_asyncio.fixture(loop_scope="function")
async def other_user(db) -> User:
    return await _seed_user(db, phone="+915550012002")


# ─────────────────────────────────────────────────────────────────────────────
# Categories
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_template(db, *, schema_hash: str) -> TemplateORM:
    """Insert a minimal templates row — Categories FK to templates with
    ``ondelete=RESTRICT``, so we need a real template_id."""
    template = TemplateORM(
        schema_hash=schema_hash,
        schema_jsonb={
            "fields": [],
            "compulsory_count": 0,
            "optional_count": 0,
            "total_count": 0,
            "wizard_step_count": 0,
            "main_sheet_label": "Test",
        },
        compliance_shape="standard",
        parsed_from_xlsx_at=datetime.now(timezone.utc),
        parser_version="test-1.0",
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


async def _seed_category(
    db,
    *,
    meesho_leaf_id: str,
    leaf_name: str,
    commission_pct: Decimal | None,
    schema_hash: str,
) -> CategoryORM:
    """Insert a minimal category row + its backing template.

    The ``categories`` DDL requires ``super_id`` / ``super_name`` / ``path``
    / ``meesho_leaf_id`` / ``leaf_name`` / ``template_id``.  Per §9
    ``commission_pct`` is the only column that pricing cares about.
    """
    template = await _seed_template(db, schema_hash=schema_hash)
    category = CategoryORM(
        super_id="99",
        super_name="Test Super",
        path=f"Test Super > {leaf_name}",
        meesho_leaf_id=meesho_leaf_id,
        leaf_name=leaf_name,
        template_id=template.id,
        commission_pct=commission_pct,
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


@pytest_asyncio.fixture(loop_scope="function")
async def priced_category(db) -> CategoryORM:
    """A category with a 15% commission — the canonical §12.J golden."""
    return await _seed_category(
        db,
        meesho_leaf_id="99001",
        leaf_name="Priced Test Leaf",
        commission_pct=Decimal("15.00"),
        schema_hash="test-priced-cat-hash-0001",
    )


@pytest_asyncio.fixture(loop_scope="function")
async def uncommissioned_category(db) -> CategoryORM:
    """A category with ``commission_pct=NULL`` — §9 surfaces this to
    pricing as ``Decimal('0.00')`` per the §9.C docstring; pricing
    raises :class:`CommissionMissingError` per §12-PRICING-D1."""
    return await _seed_category(
        db,
        meesho_leaf_id="99002",
        leaf_name="Uncommissioned Test Leaf",
        commission_pct=None,
        schema_hash="test-uncomm-cat-hash-0002",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Catalogs + Products
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_catalog(db, user_id: UUID) -> CatalogORM:
    catalog = CatalogORM(user_id=user_id, name="Test Catalog", status="draft")
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


async def _seed_product(
    db,
    *,
    user_id: UUID,
    catalog_id: UUID,
    category_id: UUID,
    name: str = "Test Product",
) -> ProductORM:
    product = ProductORM(
        user_id=user_id,
        catalog_id=catalog_id,
        category_id=category_id,
        name=name,
        status="draft",
        fields_jsonb={},
        ai_suggestions_jsonb={},
        deleted_at=None,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


@pytest_asyncio.fixture(loop_scope="function")
async def catalog_row(db, user) -> CatalogORM:
    return await _seed_catalog(db, user.id)


@pytest_asyncio.fixture(loop_scope="function")
async def product_row(db, user, catalog_row, priced_category) -> ProductORM:
    """Canonical happy-path product: owned by ``user``, under
    ``catalog_row``, pointing at ``priced_category``."""
    return await _seed_product(
        db,
        user_id=user.id,
        catalog_id=catalog_row.id,
        category_id=priced_category.id,
    )


@pytest_asyncio.fixture(loop_scope="function")
async def product_uncommissioned(
    db, user, catalog_row, uncommissioned_category
) -> ProductORM:
    """Product under ``user`` pointing at ``uncommissioned_category``.

    Used by the §12.J test #2 (commission missing): calling
    ``pricing.service.calculate`` on this product raises
    :class:`CommissionMissingError` because the §9 cross-module surface
    returns ``Decimal('0.00')`` for the missing commission."""
    return await _seed_product(
        db,
        user_id=user.id,
        catalog_id=catalog_row.id,
        category_id=uncommissioned_category.id,
        name="Uncommissioned Product",
    )


@pytest_asyncio.fixture(loop_scope="function")
async def other_user_product(db, other_user, priced_category) -> ProductORM:
    """A product owned by ``other_user`` — used by the §12.J test #1
    cross-tenant ownership-gate assertion."""
    other_catalog = await _seed_catalog(db, other_user.id)
    return await _seed_product(
        db,
        user_id=other_user.id,
        catalog_id=other_catalog.id,
        category_id=priced_category.id,
        name="Other User Product",
    )
