"""Pricing-module pytest fixtures.

Per BACKEND_ARCHITECTURE.md §12.J as superseded by the **W2 Price Calculator
rework (census-confirmed settlement model, 2026-06-19)**.

Fixtures
--------
* ``user`` — a logged-in seller.
* ``other_user`` — a second seller (cross-tenant ownership-gate test).
* ``priced_category`` — a category with a ``meesho_leaf_id`` that IS present
  in the ``meesho_pricing_lookup.json`` lookup (first key in the shipped data
  file).  This lets the full ``pricing.service.calculate`` path complete
  without raising :class:`UnknownCategoryError`.
* ``catalog_row`` — a catalog under ``user``.
* ``product_row`` — a product under ``user`` in ``catalog_row`` pointing at
  ``priced_category``.
* ``other_user_product`` — a product under ``other_user`` (cross-tenant
  fixture for the ownership-gate test).

Note: ``CommissionMissingError`` and ``product_uncommissioned`` are REMOVED
in W2 — commission is now an optional seller override (default 0), never a
missing-field failure mode.

The ``db`` fixture is the top-level conftest's ``db_session`` — fresh
ephemeral test DB (Postgres on :5432 via ``DATABASE_URL`` env in
``tests/conftest.py``).  The DB is reset per test (drop_all + create_all).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest_asyncio

from app.shared.models.catalog import Catalog as CatalogORM
from app.shared.models.category import Category as CategoryORM
from app.shared.models.product import Product as ProductORM
from app.shared.models.template import Template as TemplateORM
from app.shared.models.user import User

# Resolve a real meesho_leaf_id from the shipped lookup so integration tests
# exercise the full service path without stubbing the lookup.
_LOOKUP_FILE = (
    Path(__file__).resolve().parents[3] / "app" / "data" / "meesho_pricing_lookup.json"
)


def _first_lookup_leaf_id() -> str:
    """Return the first key in the shipped pricing lookup (real sscat_id)."""
    data = json.loads(_LOOKUP_FILE.read_text(encoding="utf-8"))
    return next(iter(data["lookup"]))


# Resolved once at import; the fixture embeds it.
_REAL_LEAF_ID: str = _first_lookup_leaf_id()


@pytest_asyncio.fixture(loop_scope="function")
async def db(db_session):
    """Alias for the ephemeral test DB session."""
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
    """Insert a minimal templates row."""
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
    schema_hash: str,
    commission_pct: Decimal | None = None,
) -> CategoryORM:
    """Insert a minimal category + its backing template."""
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
    """A category whose ``meesho_leaf_id`` is present in the pricing lookup.

    Uses the first key from ``meesho_pricing_lookup.json`` so the full
    service path (ownership → leaf resolution → shipping lookup → settlement)
    completes without :class:`UnknownCategoryError`.
    """
    return await _seed_category(
        db,
        meesho_leaf_id=_REAL_LEAF_ID,
        leaf_name="Priced Test Leaf",
        schema_hash="test-priced-cat-hash-0001",
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
    """Canonical happy-path product: owned by ``user``, pointing at
    ``priced_category`` (which has a real pricing-lookup entry)."""
    return await _seed_product(
        db,
        user_id=user.id,
        catalog_id=catalog_row.id,
        category_id=priced_category.id,
    )


@pytest_asyncio.fixture(loop_scope="function")
async def other_user_product(db, other_user, priced_category) -> ProductORM:
    """A product owned by ``other_user`` — cross-tenant ownership-gate test."""
    other_catalog = await _seed_catalog(db, other_user.id)
    return await _seed_product(
        db,
        user_id=other_user.id,
        catalog_id=other_catalog.id,
        category_id=priced_category.id,
        name="Other User Product",
    )
