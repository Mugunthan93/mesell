"""Pricing-module integration test #1 — Full create-product → set-category
→ price-calc flow.

Per BACKEND_ARCHITECTURE.md §12.J:

    Full create-product → set-category → price-calc flow.  Response
    ``commission_pct`` equals the seeded category ``commission_pct``.
    Validates end-to-end §10 + §9 + §12 cross-module wiring.

Service-level integration: invokes the cross-module call graph end-to-end
(catalog ownership gate → catalog DB read for category_id → category
commission read → pricing math → pricing_calcs INSERT → response
assembly).  HTTP-level coverage is delegated to the §15 contract suite
that exercises the full middleware chain — this test focuses on the
cross-module wiring identified in §2.D row "pricing → catalog" + "pricing
→ category".
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.pricing import service as pricing_service
from app.modules.pricing.schemas import PriceCalcRequest
from app.shared.models.catalog import Catalog as CatalogORM
from app.shared.models.category import Category as CategoryORM
from app.shared.models.product import Product as ProductORM
from app.shared.models.user import User


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# ─────────────────────────────────────────────────────────────────────────────
# Local fixtures — kept here (not in modules/pricing/conftest.py) because
# integration tests under tests/integration/ have their own conftest scope.
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_user_minimal(db, phone: str) -> User:
    user = User(phone=phone, plan="free")
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _seed_template_minimal(db, *, schema_hash: str):
    from datetime import datetime, timezone

    from app.shared.models.template import Template as TemplateORM

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


async def _seed_category_with_commission(
    db, *, meesho_leaf_id: str, leaf_name: str, commission_pct: Decimal, schema_hash: str
) -> CategoryORM:
    template = await _seed_template_minimal(db, schema_hash=schema_hash)
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


async def _seed_catalog_direct(db, *, user_id, category_id) -> CatalogORM:
    catalog = CatalogORM(user_id=user_id, name="Integration Test Catalog", status="draft", category_id=category_id)
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


async def _seed_product_direct(
    db, *, user_id, catalog_id, category_id, name: str = "Integration Test Product"
) -> ProductORM:
    """Seed a product directly via ORM — bypass catalog_service so we don't
    need the §8 customer profile-eligibility setup just to test §12 math."""
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
# Test
# ─────────────────────────────────────────────────────────────────────────────
class TestFullCreateProductToPriceCalc:
    """End-to-end §10 + §9 + §12 cross-module wiring."""

    async def test_response_commission_pct_equals_seeded_category(
        self, db_session, use_live_valkey
    ):
        """Seed a category with a known ``commission_pct``; create a
        product against it; run price-calc; assert response
        ``commission_pct`` equals the seed.

        Cross-module wiring asserted:
          * §10 catalog.assert_product_ownership — pass (same-user).
          * §9 category.get_commission — returns the seeded Decimal.
          * §12 pricing.calculate — composes the response.
        """
        # ── Seed ───────────────────────────────────────────────────────
        user = await _seed_user_minimal(db_session, phone="+915550013001")
        category = await _seed_category_with_commission(
            db_session,
            meesho_leaf_id="99100",
            leaf_name="Integration Test Leaf",
            commission_pct=Decimal("15.00"),
            schema_hash="integ-pricing-cat-0001",
        )
        catalog = await _seed_catalog_direct(
            db_session, user_id=user.id, category_id=category.id
        )
        product = await _seed_product_direct(
            db_session,
            user_id=user.id,
            catalog_id=catalog.id,
            category_id=category.id,
        )

        # ── Price-calc ─────────────────────────────────────────────────
        request = PriceCalcRequest(
            input_cost=Decimal("100"),
            target_margin_pct=Decimal("30"),
        )
        response = await pricing_service.calculate(
            user_id=user.id,
            product_id=product.id,
            request=request,
            db=db_session,
        )

        # ── Assert ─────────────────────────────────────────────────────
        # The §12.J test #1 lock: response commission_pct equals seeded.
        assert response.commission_pct == Decimal("15.00"), (
            f"Cross-module commission propagation failed: "
            f"seeded category.commission_pct=15.00, response.commission_pct="
            f"{response.commission_pct}"
        )
        # Sanity — full response shape matches the locked formula.
        assert response.seller_price == Decimal("130.00")
        assert response.mrp == Decimal("157.96")  # §12-PRICING-D2
        assert response.meesho_price == response.mrp  # V1 lock
        assert response.profit == Decimal("30.00")
        assert response.profit_pct == Decimal("30.00")
        # Alerts: profit < 50 → THIN_PROFIT fires.
        codes = {a.code for a in response.alerts}
        assert "THIN_PROFIT" in codes
        assert "LOW_MARGIN" not in codes  # profit_pct=30 ≥ 10
        assert "HIGH_MRP_MULTIPLIER" not in codes  # mrp/input ≈ 1.58 ≤ 3

    async def test_alternate_commission_propagates(
        self, db_session, use_live_valkey
    ):
        """Second commission value (5%) — verifies the wiring is not
        hardcoded to 15.  ``mrp`` shifts accordingly."""
        user = await _seed_user_minimal(db_session, phone="+915550013002")
        category = await _seed_category_with_commission(
            db_session,
            meesho_leaf_id="99101",
            leaf_name="Integration Alt Leaf",
            commission_pct=Decimal("5.00"),
            schema_hash="integ-pricing-cat-0002",
        )
        catalog = await _seed_catalog_direct(
            db_session, user_id=user.id, category_id=category.id
        )
        product = await _seed_product_direct(
            db_session,
            user_id=user.id,
            catalog_id=catalog.id,
            category_id=category.id,
        )

        response = await pricing_service.calculate(
            user_id=user.id,
            product_id=product.id,
            request=PriceCalcRequest(
                input_cost=Decimal("100"),
                target_margin_pct=Decimal("30"),
            ),
            db=db_session,
        )

        assert response.commission_pct == Decimal("5.00")
        # denom = 1 - 0.05 - 0.18 × 0.05 = 1 - 0.05 - 0.009 = 0.941
        # mrp = 130 / 0.941 ≈ 138.15 (ROUND_HALF_EVEN)
        assert response.mrp == Decimal("138.15"), (
            f"5% commission case: expected mrp=138.15, got {response.mrp}"
        )
