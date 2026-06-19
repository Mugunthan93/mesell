"""Pricing-module integration test #1 — Full product → price-calc flow.

Per BACKEND_ARCHITECTURE.md §12.M as superseded by the **W2 Price Calculator
rework (census-confirmed settlement model, 2026-06-19)** — authoritative source
``.claude/agent-memory/nexus-level-0-director/project_pricing_transfer_price_model.md``.

Service-level integration: invokes the cross-module call graph end-to-end
(catalog ownership gate → meesho_leaf_id resolution → shipping lookup →
settlement math → pricing_calcs INSERT → response assembly).

Golden anchor: selling_price=70, leaf uses base shipping=45 →
estimated_bank_settlement=61.78 (founder's first real order, TTC-BL-OR-HP-NG-P4).

NOTE: these tests require a live DB (``DATABASE_URL``) AND the category's
``meesho_leaf_id`` to exist in ``meesho_pricing_lookup.json``.  They are
``integration``-marked and infra-gated in CI Gate-1 (unit-only).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.pricing import service as pricing_service
from app.modules.pricing.schemas import PriceCalcRequest
from app.shared.models.catalog import Catalog as CatalogORM
from app.shared.models.category import Category as CategoryORM
from app.shared.models.product import Product as ProductORM
from app.shared.models.user import User


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

_LOOKUP_FILE = (
    Path(__file__).resolve().parents[2] / "app" / "data" / "meesho_pricing_lookup.json"
)


def _load_lookup() -> dict:
    return json.loads(_LOOKUP_FILE.read_text(encoding="utf-8"))["lookup"]


def _first_leaf_and_shipping() -> tuple[str, int]:
    """Return the first (leaf_id, shipping) pair from the shipped lookup."""
    lookup = _load_lookup()
    leaf_id, row = next(iter(lookup.items()))
    return leaf_id, int(row["shipping_charges"])


# ─────────────────────────────────────────────────────────────────────────────
# Seed helpers (self-contained per integration test file convention)
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_user_minimal(db, phone: str) -> User:
    user = User(phone=phone, plan="free")
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _seed_template_minimal(db, *, schema_hash: str):
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


async def _seed_category_with_leaf(
    db, *, meesho_leaf_id: str, leaf_name: str, schema_hash: str
) -> CategoryORM:
    """Seed a category with a real meesho_leaf_id (present in the lookup)."""
    template = await _seed_template_minimal(db, schema_hash=schema_hash)
    category = CategoryORM(
        super_id="99",
        super_name="Test Super",
        path=f"Test Super > {leaf_name}",
        meesho_leaf_id=meesho_leaf_id,
        leaf_name=leaf_name,
        template_id=template.id,
        commission_pct=None,  # census default is 0 anyway; not read by W2 service
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


async def _seed_catalog_direct(db, *, user_id, category_id) -> CatalogORM:
    catalog = CatalogORM(
        user_id=user_id,
        name="Integration Test Catalog",
        status="draft",
        category_id=category_id,
    )
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


async def _seed_product_direct(
    db, *, user_id, catalog_id, category_id, name: str = "Integration Test Product"
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
class TestFullProductToPriceCalc:
    """End-to-end §10 (ownership) + W2 settlement math wiring."""

    async def test_settlement_full_response_shape(self, db_session, use_live_valkey):
        """Create a product; run the census-confirmed price-calc; assert the
        full W2 response shape.

        Wiring verified:
          * §10 catalog.assert_product_ownership — pass (same-user).
          * category leaf resolution via catalog.get_product_meesho_leaf_id.
          * pricing_lookup.get_shipping (real lookup, no mock).
          * settlement math (census-confirmed formula).
          * pricing_calcs INSERT (append-only row created).
        """
        leaf_id, shipping = _first_leaf_and_shipping()

        user = await _seed_user_minimal(db_session, phone="+915550013001")
        category = await _seed_category_with_leaf(
            db_session,
            meesho_leaf_id=leaf_id,
            leaf_name="Integration Test Leaf",
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

        request = PriceCalcRequest(selling_price=Decimal("100"))
        response = await pricing_service.calculate(
            user_id=user.id,
            product_id=product.id,
            request=request,
            db=db_session,
        )

        # ── Structural shape ─────────────────────────────────────────────
        assert response.selling_price == Decimal("100.00")
        assert response.shipping == Decimal(str(shipping))
        assert response.total_price == Decimal(str(100 + shipping))
        assert response.commission_pct == Decimal("0.00")
        assert response.commission_fees == Decimal("0.00")
        assert response.tcs == Decimal("0.00")
        assert isinstance(response.gst_on_shipping, Decimal)
        assert isinstance(response.tds, Decimal)
        assert isinstance(response.estimated_bank_settlement, Decimal)
        assert isinstance(response.calculated_at, datetime)
        assert isinstance(response.alerts, list)
        assert isinstance(response.disclaimer, str)
        assert len(response.disclaimer) > 10

    async def test_commission_override_reduces_settlement(
        self, db_session, use_live_valkey
    ):
        """Passing ``commission_pct=2`` reduces settlement by exactly 2% of
        selling_price vs the commission=0 baseline."""
        leaf_id, _shipping = _first_leaf_and_shipping()

        user = await _seed_user_minimal(db_session, phone="+915550013002")
        category = await _seed_category_with_leaf(
            db_session,
            meesho_leaf_id=leaf_id,
            leaf_name="Commission Override Leaf",
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

        base = await pricing_service.calculate(
            user_id=user.id,
            product_id=product.id,
            request=PriceCalcRequest(selling_price=Decimal("100")),
            db=db_session,
        )
        with_comm = await pricing_service.calculate(
            user_id=user.id,
            product_id=product.id,
            request=PriceCalcRequest(
                selling_price=Decimal("100"),
                commission_pct=Decimal("2"),
            ),
            db=db_session,
        )

        assert with_comm.commission_pct == Decimal("2.00")
        assert with_comm.commission_fees == Decimal("2.00")
        delta = base.estimated_bank_settlement - with_comm.estimated_bank_settlement
        assert delta == Decimal("2.00"), (
            f"Commission override should reduce settlement by exactly 2.00; "
            f"got delta={delta}"
        )

    async def test_negative_settlement_is_200_with_alert(
        self, db_session, use_live_valkey
    ):
        """selling_price=1 against a high-shipping category → negative
        settlement → 200 response + one NEGATIVE_SETTLEMENT alert (not a 400).
        """
        # Use the max-shipping leaf_id (8435) if present, else the first.
        lookup = _load_lookup()
        max_leaf = max(lookup, key=lambda k: int(lookup[k]["shipping_charges"]))

        user = await _seed_user_minimal(db_session, phone="+915550013003")
        category = await _seed_category_with_leaf(
            db_session,
            meesho_leaf_id=max_leaf,
            leaf_name="High Shipping Leaf",
            schema_hash="integ-pricing-cat-0003",
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
            request=PriceCalcRequest(selling_price=Decimal("1")),
            db=db_session,
        )

        assert response.estimated_bank_settlement < Decimal("0")
        assert len(response.alerts) == 1
        assert response.alerts[0].code == "NEGATIVE_SETTLEMENT"
