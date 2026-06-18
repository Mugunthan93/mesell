"""Pricing-module integration test #1 — Full product → price-calc flow.

Per BACKEND_ARCHITECTURE.md §12.M AMENDMENT 2026-06-18 (forward estimator).

Service-level integration: invokes the cross-module call graph end-to-end
(catalog ownership gate → forward payout estimator → pricing_calcs INSERT
→ response assembly).  Per §12.M the ``pricing → category`` commission
read is RETIRED — commission is a seller input.  HTTP-level coverage is
delegated to the §15 contract suite; this test focuses on the
``pricing → catalog`` ownership wiring + the forward estimator output.
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
class TestFullProductToPriceCalc:
    """End-to-end §10 (ownership) + §12.M (forward estimator) wiring."""

    async def test_forward_estimator_full_response_shape(
        self, db_session, use_live_valkey
    ):
        """Create a product; run the forward price-calc; assert the full
        response shape against the §12.M estimator.

        Wiring asserted:
          * §10 catalog.assert_product_ownership — pass (same-user).
          * §12.M pricing.calculate — composes the forward response.
        """
        # ── Seed ───────────────────────────────────────────────────────
        user = await _seed_user_minimal(db_session, phone="+915550013001")
        category = await _seed_category_with_commission(
            db_session,
            meesho_leaf_id="99100",
            leaf_name="Integration Test Leaf",
            commission_pct=Decimal("15.00"),  # ignored by §12.M — seller input wins
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

        # ── Price-calc (forward) ───────────────────────────────────────
        request = PriceCalcRequest(
            meesho_price=Decimal("106"),
            input_cost=Decimal("40"),
        )
        response = await pricing_service.calculate(
            user_id=user.id,
            product_id=product.id,
            request=request,
            db=db_session,
        )

        # ── Assert — calibrated estimator output ───────────────────────
        assert response.meesho_price == Decimal("106.00")
        assert response.commission_pct == Decimal("4.00")  # seller-input default
        assert response.estimated_payout == Decimal("46.84")  # calibration
        assert response.profit == Decimal("6.84")  # 46.84 − 40
        assert response.wdrp_price == Decimal("86.00")  # 106 − WDRP_DELTA(20)
        assert response.estimated_payout_wdrp == Decimal("27.98")
        # margin_pct = 6.84 / 106 × 100 ≈ 6.45 → LOW_MARGIN fires.
        codes = {a.code for a in response.alerts}
        assert "LOW_MARGIN" in codes
        assert "SHIPPING_DOMINATES" in codes  # shipping 30 of ~59.16 > 40%
        assert "NEGATIVE_PAYOUT" not in codes  # payout positive

    async def test_seller_commission_input_drives_referral(
        self, db_session, use_live_valkey
    ):
        """A higher seller-entered commission_pct raises the referral
        deduction and lowers the payout — proving commission is a seller
        input, not a category lookup."""
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
                meesho_price=Decimal("500"),
                input_cost=Decimal("100"),
                commission_pct=Decimal("10"),  # seller input, NOT the seeded 5%
            ),
            db=db_session,
        )

        assert response.commission_pct == Decimal("10.00")
        # referral = 500 × 10% = 50.00 (echoes the seller input, not the seed)
        assert response.referral_commission == Decimal("50.00")
