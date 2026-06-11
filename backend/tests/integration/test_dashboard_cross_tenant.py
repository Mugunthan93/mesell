"""Dashboard-module integration test #2 per §13.J.

The tenancy contract verified end-to-end through dashboard.

Per BACKEND_ARCHITECTURE.md §13.J integration #2:

    "User A has 3 products, User B has 2 products. User A's `GET /products`
    returns ONLY A's 3 products + `total=3`. User B's `GET /products`
    returns ONLY B's 2 products + `total=2`. The enforcement is in
    `catalog.service.list_products`' repository layer per §10.D, but this
    integration test verifies the cross-tenant scope is respected
    end-to-end through the dashboard surface — guarding against any
    future refactor that might leak User A's rows into User B's response."

This is the structural seam that protects the multi-tenant contract.
Dashboard does NOT enforce tenancy itself (§13.D — no repository); it
delegates to catalog (§10.D scope_to_user) + customer (§8.D scope_to_user).
This test guards the contract from above so any future refactor that
breaks the seam fails CI here, not in production.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.modules.dashboard import service as dashboard_service
from app.modules.dashboard.schemas import DashboardQuery
from app.shared.models.catalog import Catalog as CatalogORM
from app.shared.models.category import Category as CategoryORM
from app.shared.models.product import Product as ProductORM
from app.shared.models.template import Template as TemplateORM
from app.shared.models.user import User


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# ─────────────────────────────────────────────────────────────────────────────
# Local seed helpers
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_user(db, *, phone: str) -> User:
    user = User(phone=phone, plan="free")
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _seed_template(db, *, schema_hash: str) -> TemplateORM:
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
        parser_version="dash1.0",
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


async def _seed_category(db, *, schema_hash: str, leaf_id: str, leaf_name: str) -> CategoryORM:
    template = await _seed_template(db, schema_hash=schema_hash)
    category = CategoryORM(
        super_id="99",
        super_name="Tenant Test Super",
        path=f"Tenant Test Super > {leaf_name}",
        meesho_leaf_id=leaf_id,
        leaf_name=leaf_name,
        template_id=template.id,
        commission_pct=Decimal("10.00"),
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


async def _seed_catalog(db, *, user_id, category_id, name: str) -> CatalogORM:
    catalog = CatalogORM(
        user_id=user_id,
        name=name,
        status="draft",
        category_id=category_id,
    )
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


async def _seed_product(db, *, user_id, catalog_id, category_id, name: str) -> ProductORM:
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


# ─────────────────────────────────────────────────────────────────────────────
# Test class
# ─────────────────────────────────────────────────────────────────────────────
class TestDashboardCrossTenantIsolation:
    """The §10.D + §8.D ``scope_to_user`` contract verified through dashboard."""

    async def test_user_a_sees_only_a_products_user_b_sees_only_b_products(
        self, db_session, use_live_valkey
    ):
        """User A: 3 products. User B: 2 products. Each sees only their own.

        The leakage-guard contract is: ``dashboard.service.list_products_for_dashboard``
        forwards the ``user_id`` parameter to both consumed services, and
        each service's repository layer enforces ``scope_to_user(user_id)``
        on every SQL statement.  Any future refactor that drops the
        ``user_id`` from the call chain would surface here as a leaked row
        between users.
        """
        # ── Seed two users + their products ────────────────────────────
        user_a = await _seed_user(db_session, phone="+915550015001")
        user_b = await _seed_user(db_session, phone="+915550015002")

        category = await _seed_category(
            db_session,
            schema_hash="dashboard-tenant-0001",
            leaf_id="TENANT-LEAF-1",
            leaf_name="Tenant Test Leaf",
        )

        catalog_a = await _seed_catalog(
            db_session, user_id=user_a.id, category_id=category.id, name="User A Catalog"
        )
        catalog_b = await _seed_catalog(
            db_session, user_id=user_b.id, category_id=category.id, name="User B Catalog"
        )

        # User A: 3 products
        for idx in range(3):
            await _seed_product(
                db_session,
                user_id=user_a.id,
                catalog_id=catalog_a.id,
                category_id=category.id,
                name=f"A Product {idx + 1}",
            )

        # User B: 2 products
        for idx in range(2):
            await _seed_product(
                db_session,
                user_id=user_b.id,
                catalog_id=catalog_b.id,
                category_id=category.id,
                name=f"B Product {idx + 1}",
            )

        await db_session.commit()

        # ── User A's dashboard call ────────────────────────────────────
        query = DashboardQuery(page=1, limit=20)
        response_a = await dashboard_service.list_products_for_dashboard(
            user_id=user_a.id,
            query=query,
            db=db_session,
        )

        # ── Assert: ONLY A's 3 products, total=3 ───────────────────────
        assert response_a.total == 3
        assert len(response_a.products) == 3
        names_a = {p.name for p in response_a.products}
        assert names_a == {"A Product 1", "A Product 2", "A Product 3"}
        # NO B-products may leak.
        for item in response_a.products:
            assert item.name is None or not item.name.startswith("B Product"), (
                "User A's dashboard leaked a B-prefixed product — §10.D "
                "scope_to_user contract violated."
            )

        # ── User B's dashboard call ────────────────────────────────────
        response_b = await dashboard_service.list_products_for_dashboard(
            user_id=user_b.id,
            query=query,
            db=db_session,
        )

        # ── Assert: ONLY B's 2 products, total=2 ───────────────────────
        assert response_b.total == 2
        assert len(response_b.products) == 2
        names_b = {p.name for p in response_b.products}
        assert names_b == {"B Product 1", "B Product 2"}
        for item in response_b.products:
            assert item.name is None or not item.name.startswith("A Product"), (
                "User B's dashboard leaked an A-prefixed product — §10.D "
                "scope_to_user contract violated."
            )

        # ── Cross-totals must NOT sum across tenants ───────────────────
        assert response_a.total != response_b.total, (
            "Tenants returned the SAME total — the scope filter is plausibly "
            "missing.  A=3, B=2 are deliberately distinct to make this guard "
            "actionable."
        )

    async def test_user_with_zero_products_does_not_see_other_users_products(
        self, db_session, use_live_valkey
    ):
        """A first-time seller with zero products must see an empty list
        even when other users have products in the database.
        """
        user_a = await _seed_user(db_session, phone="+915550015003")
        user_c = await _seed_user(db_session, phone="+915550015004")  # the zero-product user

        category = await _seed_category(
            db_session,
            schema_hash="dashboard-tenant-0002",
            leaf_id="TENANT-LEAF-2",
            leaf_name="Tenant Test Leaf 2",
        )
        catalog_a = await _seed_catalog(
            db_session, user_id=user_a.id, category_id=category.id, name="User A Catalog 2"
        )
        for idx in range(4):
            await _seed_product(
                db_session,
                user_id=user_a.id,
                catalog_id=catalog_a.id,
                category_id=category.id,
                name=f"A Product 2-{idx + 1}",
            )
        await db_session.commit()

        # User C (zero products) calls dashboard.
        query = DashboardQuery(page=1, limit=20)
        response_c = await dashboard_service.list_products_for_dashboard(
            user_id=user_c.id,
            query=query,
            db=db_session,
        )

        # User C must see exactly nothing — NOT user A's 4 products.
        assert response_c.total == 0
        assert response_c.products == []
