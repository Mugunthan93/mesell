"""Pricing-module integration test #2 — pricing_calcs persistence +
get_last_calc.

Per BACKEND_ARCHITECTURE.md §12.J as superseded by the **W2 Price Calculator
rework (census-confirmed settlement model, 2026-06-19)**.

Verifies:
  * A single ``calculate`` call writes ONE ``pricing_calcs`` row carrying
    ALL confirmed-model columns (selling_price, shipping, total_price,
    commission_pct, commission_fees, gst_on_shipping, tds, tcs,
    estimated_bank_settlement, meesho_leaf_id).
  * The deprecated #285 columns (meesho_price, seller_price, etc.) are NULL.
  * ``get_last_calc`` returns the most recent calc for a product.
  * Subsequent calcs INSERT new rows (append-only, not UPDATE).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from app.modules.pricing import service as pricing_service
from app.modules.pricing.schemas import PriceCalcRequest
from app.shared.models.catalog import Catalog as CatalogORM
from app.shared.models.category import Category as CategoryORM
from app.shared.models.pricing_calc import PricingCalc as PricingCalcORM
from app.shared.models.product import Product as ProductORM
from app.shared.models.user import User


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

_LOOKUP_FILE = (
    Path(__file__).resolve().parents[2] / "app" / "data" / "meesho_pricing_lookup.json"
)


def _first_leaf_id() -> str:
    data = json.loads(_LOOKUP_FILE.read_text(encoding="utf-8"))
    return next(iter(data["lookup"]))


_REAL_LEAF_ID: str = _first_leaf_id()


# ─────────────────────────────────────────────────────────────────────────────
# Seed helpers
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_user(db, phone: str) -> User:
    user = User(phone=phone, plan="free")
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _seed_template(db, *, schema_hash: str):
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


async def _seed_category(
    db, *, meesho_leaf_id: str, leaf_name: str, schema_hash: str
) -> CategoryORM:
    template = await _seed_template(db, schema_hash=schema_hash)
    category = CategoryORM(
        super_id="99",
        super_name="Test Super",
        path=f"Test Super > {leaf_name}",
        meesho_leaf_id=meesho_leaf_id,
        leaf_name=leaf_name,
        template_id=template.id,
        commission_pct=None,
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


async def _seed_catalog(db, *, user_id) -> CatalogORM:
    catalog = CatalogORM(
        user_id=user_id, name="Persistence Test Catalog", status="draft"
    )
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


async def _seed_product(
    db,
    *,
    user_id,
    catalog_id,
    category_id,
    name: str = "Persistence Test Product",
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


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestPricingCalcsPersistence:
    """Append-only audit trail + confirmed-model column persistence."""

    async def test_calc_writes_confirmed_model_columns(
        self, db_session, use_live_valkey
    ):
        """A single ``calculate`` call writes ONE ``pricing_calcs`` row with
        all confirmed-model columns populated and all deprecated #285 columns
        left NULL.
        """
        user = await _seed_user(db_session, "+915550014001")
        category = await _seed_category(
            db_session,
            meesho_leaf_id=_REAL_LEAF_ID,
            leaf_name="Persistence Leaf",
            schema_hash="integ-pricing-persist-0001",
        )
        catalog = await _seed_catalog(db_session, user_id=user.id)
        product = await _seed_product(
            db_session,
            user_id=user.id,
            catalog_id=catalog.id,
            category_id=category.id,
        )

        response = await pricing_service.calculate(
            user_id=user.id,
            product_id=product.id,
            request=PriceCalcRequest(selling_price=Decimal("100")),
            db=db_session,
        )

        # ── Find the row ─────────────────────────────────────────────────
        result = await db_session.execute(
            select(PricingCalcORM).where(PricingCalcORM.product_id == product.id)
        )
        rows = result.scalars().all()
        assert len(rows) == 1, (
            f"Expected 1 pricing_calcs row after a single calc; got {len(rows)}"
        )
        row = rows[0]

        # ── Confirmed-model columns match the response ────────────────────
        assert row.selling_price == response.selling_price
        assert row.shipping == response.shipping
        assert row.total_price == response.total_price
        assert row.commission_pct == response.commission_pct
        assert row.commission_fees == response.commission_fees
        assert row.gst_on_shipping == response.gst_on_shipping
        assert row.tds == response.tds
        assert row.tcs == response.tcs
        assert row.estimated_bank_settlement == response.estimated_bank_settlement
        assert row.meesho_leaf_id == _REAL_LEAF_ID

        # ── Deprecated #285 columns must be NULL (never written by W2+) ──
        assert row.meesho_price is None, (
            f"Deprecated meesho_price should be NULL, got {row.meesho_price}"
        )
        assert row.seller_price is None, (
            f"Deprecated seller_price should be NULL, got {row.seller_price}"
        )
        assert row.estimated_payout is None, (
            f"Deprecated estimated_payout should be NULL, got {row.estimated_payout}"
        )
        assert row.logistics_fee is None
        assert row.fixed_fee is None
        assert row.gst_on_fees is None
        assert row.rto_expected_loss is None
        assert row.wdrp_price is None

        assert row.created_at is not None

    async def test_append_only_three_rows_for_three_calcs(
        self, db_session, use_live_valkey
    ):
        """Three sequential calcs INSERT THREE rows (not one UPDATEd row).

        The append-only invariant (§12.B.1 step 8 / §12-PRICING-D4) is
        verified by counting rows after three distinct commits.
        """
        import asyncio

        user = await _seed_user(db_session, "+915550014002")
        category = await _seed_category(
            db_session,
            meesho_leaf_id=_REAL_LEAF_ID,
            leaf_name="Sequential Leaf",
            schema_hash="integ-pricing-persist-0002",
        )
        catalog = await _seed_catalog(db_session, user_id=user.id)
        product = await _seed_product(
            db_session,
            user_id=user.id,
            catalog_id=catalog.id,
            category_id=category.id,
        )
        await db_session.commit()

        for price in (Decimal("100"), Decimal("200"), Decimal("300")):
            await pricing_service.calculate(
                user_id=user.id,
                product_id=product.id,
                request=PriceCalcRequest(selling_price=price),
                db=db_session,
            )
            await db_session.commit()
            await asyncio.sleep(0.01)

        result = await db_session.execute(
            select(PricingCalcORM)
            .where(PricingCalcORM.product_id == product.id)
            .order_by(PricingCalcORM.created_at.asc())
        )
        rows = result.scalars().all()
        assert len(rows) == 3, (
            f"Append-only invariant violated: expected 3 rows, got {len(rows)}"
        )
        # Each row's selling_price reflects its distinct input.
        selling_prices = sorted(r.selling_price for r in rows)
        assert selling_prices == [
            Decimal("100.00"),
            Decimal("200.00"),
            Decimal("300.00"),
        ]

    async def test_get_last_calc_returns_most_recent(
        self, db_session, use_live_valkey
    ):
        """``get_last_calc`` returns the most recently committed row."""
        import asyncio
        from datetime import timedelta

        user = await _seed_user(db_session, "+915550014003")
        category = await _seed_category(
            db_session,
            meesho_leaf_id=_REAL_LEAF_ID,
            leaf_name="LastCalc Leaf",
            schema_hash="integ-pricing-persist-0003",
        )
        catalog = await _seed_catalog(db_session, user_id=user.id)
        product = await _seed_product(
            db_session,
            user_id=user.id,
            catalog_id=catalog.id,
            category_id=category.id,
        )
        await db_session.commit()

        for price in (Decimal("100"), Decimal("200"), Decimal("500")):
            await pricing_service.calculate(
                user_id=user.id,
                product_id=product.id,
                request=PriceCalcRequest(selling_price=price),
                db=db_session,
            )
            await db_session.commit()
            await asyncio.sleep(0.01)

        # Monotonically stamp created_at so ORDER BY is deterministic under
        # the test harness (same txn NOW() artifact).
        result = await db_session.execute(
            select(PricingCalcORM)
            .where(PricingCalcORM.product_id == product.id)
            .order_by(PricingCalcORM.selling_price.asc())
        )
        rows = result.scalars().all()
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i, row in enumerate(rows):
            row.created_at = base + timedelta(seconds=i)
        await db_session.flush()

        latest = await pricing_service.get_last_calc(
            user_id=user.id,
            product_id=product.id,
            db=db_session,
        )
        assert latest is not None
        assert latest.selling_price == Decimal("500.00"), (
            f"get_last_calc should return the most recent (selling_price=500); "
            f"got selling_price={latest.selling_price}"
        )

    async def test_get_last_calc_returns_none_for_no_history(
        self, db_session, use_live_valkey
    ):
        """A product with no calc history → ``get_last_calc`` returns None."""
        user = await _seed_user(db_session, "+915550014004")
        category = await _seed_category(
            db_session,
            meesho_leaf_id=_REAL_LEAF_ID,
            leaf_name="No-History Leaf",
            schema_hash="integ-pricing-persist-0004",
        )
        catalog = await _seed_catalog(db_session, user_id=user.id)
        product = await _seed_product(
            db_session,
            user_id=user.id,
            catalog_id=catalog.id,
            category_id=category.id,
        )

        latest = await pricing_service.get_last_calc(
            user_id=user.id,
            product_id=product.id,
            db=db_session,
        )
        assert latest is None
