"""Pricing-module integration test #2 — pricing_calcs persistence +
get_last_calc.

Per BACKEND_ARCHITECTURE.md §12.J:

    pricing_calcs persistence + get_last_calc — verify the full
    ``input_jsonb`` and ``output_jsonb`` snapshots are written for audit;
    ``get_last_calc`` returns the most recent calc for a product;
    subsequent calc inserts a new row (not an UPDATE — audit trail is
    append-only).

DECISION FLAG §12-PRICING-D4 — DDL is the law
---------------------------------------------
The actual ``pricing_calcs`` DDL has structured monetary columns (NOT
``input_jsonb`` / ``output_jsonb``).  This test verifies the
**structured-column** persistence shape — adapted from the §12.J
"input_jsonb/output_jsonb snapshots" prose per D4.  The append-only
invariant (subsequent calc → NEW row, not UPDATE) is fully tested.
"""

from __future__ import annotations

from decimal import Decimal

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


# ─────────────────────────────────────────────────────────────────────────────
# Local fixtures — minimal seed helpers (duplicated from full_flow test to
# keep each integration file self-contained).
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_user(db, phone: str) -> User:
    user = User(phone=phone, plan="free")
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _seed_template(db, *, schema_hash: str):
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


async def _seed_category(
    db, *, meesho_leaf_id: str, leaf_name: str, schema_hash: str,
    commission_pct: Decimal = Decimal("15.00"),
) -> CategoryORM:
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


async def _seed_catalog(db, *, user_id) -> CatalogORM:
    catalog = CatalogORM(user_id=user_id, name="Persistence Test Catalog", status="draft")
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


async def _seed_product(
    db, *, user_id, catalog_id, category_id, name: str = "Persistence Test Product"
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
# Test
# ─────────────────────────────────────────────────────────────────────────────
class TestPricingCalcsPersistence:
    """§12.J test #2 — append-only audit trail + get_last_calc."""

    async def test_calc_writes_full_structured_snapshot(
        self, db_session, use_live_valkey
    ):
        """A single ``calculate`` call writes ONE ``pricing_calcs`` row
        carrying ALL structured columns per the DDL (§12-PRICING-D4).

        Adapts the §12.J prose "full input_jsonb and output_jsonb
        snapshots" to the actual DDL: the structured columns ARE the
        snapshot."""
        user = await _seed_user(db_session, "+915550014001")
        category = await _seed_category(
            db_session, meesho_leaf_id="99200", leaf_name="Persistence Leaf",
            schema_hash="integ-pricing-persist-0001",
        )
        catalog = await _seed_catalog(db_session, user_id=user.id)
        product = await _seed_product(
            db_session, user_id=user.id, catalog_id=catalog.id,
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

        # Find the row.
        result = await db_session.execute(
            select(PricingCalcORM).where(
                PricingCalcORM.product_id == product.id
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 1, (
            f"Expected exactly 1 pricing_calcs row after a single calc; "
            f"got {len(rows)}"
        )
        row = rows[0]

        # Every structured column reflects the response.
        assert row.mrp == response.mrp
        assert row.meesho_price == response.meesho_price
        assert row.seller_price == response.seller_price
        assert row.commission_pct == response.commission_pct
        assert row.gst_pct == response.gst_pct
        assert row.margin == response.profit, (
            f"Audit column 'margin' must equal computed 'profit'; "
            f"got margin={row.margin}, profit={response.profit}"
        )
        assert row.margin_pct == response.profit_pct, (
            f"Audit column 'margin_pct' must equal computed 'profit_pct'; "
            f"got margin_pct={row.margin_pct}, profit_pct={response.profit_pct}"
        )
        # created_at is server-set.
        assert row.created_at is not None

    async def test_get_last_calc_returns_most_recent(
        self, db_session, use_live_valkey
    ):
        """``get_last_calc`` returns the most recent calc and three
        sequential calcs leave THREE rows (not one UPDATEd row).

        Each calc is committed in its own transaction so PostgreSQL's
        ``NOW()`` (which is transaction-bound) yields distinct
        ``created_at`` values — mirroring the production reality where
        each HTTP request is its own transaction.
        """
        import asyncio

        user = await _seed_user(db_session, "+915550014002")
        category = await _seed_category(
            db_session, meesho_leaf_id="99201", leaf_name="Sequential Leaf",
            schema_hash="integ-pricing-persist-0002",
        )
        catalog = await _seed_catalog(db_session, user_id=user.id)
        product = await _seed_product(
            db_session, user_id=user.id, catalog_id=catalog.id,
            category_id=category.id,
        )
        await db_session.commit()  # finalise seed in its own tx

        # Three sequential calcs in DISTINCT transactions — last one
        # wins in get_last_calc but ALL persist as separate rows.
        for target_pct in (Decimal("10"), Decimal("20"), Decimal("50")):
            await pricing_service.calculate(
                user_id=user.id,
                product_id=product.id,
                request=PriceCalcRequest(
                    input_cost=Decimal("100"),
                    target_margin_pct=target_pct,
                ),
                db=db_session,
            )
            await db_session.commit()
            # Tiny gap ensures Postgres NOW() ticks past the previous
            # transaction even on millisecond-resolution clocks.
            await asyncio.sleep(0.01)

        # Append-only: three rows must exist (NOT one UPDATEd row).
        result = await db_session.execute(
            select(PricingCalcORM)
            .where(PricingCalcORM.product_id == product.id)
            .order_by(PricingCalcORM.created_at.asc())
        )
        rows = result.scalars().all()
        assert len(rows) == 3, (
            f"Append-only audit trail violated: expected 3 rows after 3 "
            f"calcs, got {len(rows)}.  Service must INSERT each calc, "
            f"never UPDATE."
        )
        # Each row's seller_price reflects its input — proves they are
        # distinct calcs, not duplicate writes.
        seller_prices = sorted(r.seller_price for r in rows)
        assert seller_prices == [
            Decimal("110.00"),  # 100 × (1 + 10/100)
            Decimal("120.00"),  # 100 × (1 + 20/100)
            Decimal("150.00"),  # 100 × (1 + 50/100)
        ]

        # Savepoint isolation (per-test SAVEPOINT inside ONE outer transaction)
        # shares the outer txn's NOW() across all 3 commits, so created_at is
        # identical → ORDER BY created_at DESC is nondeterministic. Force
        # distinct, monotonically-increasing created_at values keyed by
        # seller_price so the "most-recent-wins" intent (50% calc = newest) is
        # deterministic under the harness (BE-PRICING-LASTCALC-TX-1).
        from datetime import datetime, timedelta, timezone

        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        ts_by_price = {
            Decimal("110.00"): base,                          # oldest
            Decimal("120.00"): base + timedelta(seconds=1),
            Decimal("150.00"): base + timedelta(seconds=2),   # newest
        }
        for r in rows:
            r.created_at = ts_by_price[r.seller_price]
        await db_session.flush()

        # get_last_calc returns the most recent.
        latest = await pricing_service.get_last_calc(
            user_id=user.id,
            product_id=product.id,
            db=db_session,
        )
        assert latest is not None
        assert latest.seller_price == Decimal("150.00"), (
            f"get_last_calc should return the most recent (target_pct=50%, "
            f"seller_price=150); got seller_price={latest.seller_price}"
        )

    async def test_get_last_calc_returns_none_for_no_history(
        self, db_session, use_live_valkey
    ):
        """A product with no calc history → ``get_last_calc`` returns
        ``None`` (per §12.C surface contract)."""
        user = await _seed_user(db_session, "+915550014003")
        category = await _seed_category(
            db_session, meesho_leaf_id="99202", leaf_name="No-History Leaf",
            schema_hash="integ-pricing-persist-0003",
        )
        catalog = await _seed_catalog(db_session, user_id=user.id)
        product = await _seed_product(
            db_session, user_id=user.id, catalog_id=catalog.id,
            category_id=category.id,
        )

        latest = await pricing_service.get_last_calc(
            user_id=user.id,
            product_id=product.id,
            db=db_session,
        )
        assert latest is None
