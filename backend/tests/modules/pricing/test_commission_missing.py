"""Pricing-module unit test #2 — Commission missing.

Per BACKEND_ARCHITECTURE.md §12.J:

    Commission missing — when ``category.get_commission`` returns
    ``None`` (mocked) → 422 ``pricing.commission_missing``.  Validates
    the §12.G :class:`CommissionMissingError` path.

DECISION FLAG §12-PRICING-D1 — get_commission returns Decimal('0.00')
--------------------------------------------------------------------
The §9 implementation (Wave 3 LOCKED) returns ``Decimal('0.00')`` for
the missing-commission case (not ``None``), per its docstring: "NEVER
None — categories without a seeded commission have no pricing surface
in V1; the pricing service fails over to a default".

Pricing treats the zero-return as the missing-signal and raises
:class:`CommissionMissingError`.  This test verifies that behavior in
TWO ways:

1. Real DB path — a category with ``commission_pct=NULL`` in the DB:
   §9 surfaces ``Decimal('0.00')``; pricing raises.  Locks the
   end-to-end seam from DB null → service exception.
2. Mocked path — monkeypatch ``category_service.get_commission`` to
   return ``Decimal('0.00')`` directly, mirroring the §12.J prose
   "(mocked)" — locks the same seam from a unit perspective without
   depending on §9 internals.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.pricing import service as pricing_service
from app.modules.pricing.exceptions import CommissionMissingError
from app.modules.pricing.schemas import PriceCalcRequest


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


class TestCommissionMissing:
    """Two complementary assertions on the §12-PRICING-D1 missing-commission
    path."""

    async def test_db_null_commission_raises_commission_missing(
        self, db, user, product_uncommissioned, use_live_valkey
    ):
        """End-to-end — DB row has ``commission_pct=NULL``; §9 returns
        ``Decimal('0.00')``; §12 raises :class:`CommissionMissingError`.

        The §12-PRICING-D1 contract is end-to-end: an unseeded category
        row in the DB triggers the 422 path."""
        request = PriceCalcRequest(
            input_cost=Decimal("100"),
            target_margin_pct=Decimal("30"),
        )

        with pytest.raises(CommissionMissingError) as exc_info:
            await pricing_service.calculate(
                user_id=user.id,
                product_id=product_uncommissioned.id,
                request=request,
                db=db,
            )

        # Verify the exception carries the locked envelope identifiers
        # so the §4.F handler emits the right 422 envelope.
        assert exc_info.value.status_code == 422
        assert exc_info.value.code == "pricing.commission_missing"
        assert exc_info.value.validation_message_id == "pricing.commission.missing", (
            "§12-PRICING-D3a — 3-segment ID per §5A.H regex"
        )

    async def test_mocked_zero_commission_raises_commission_missing(
        self, db, user, product_row, use_live_valkey, monkeypatch
    ):
        """Service-level — mock ``category_service.get_commission`` to
        return ``Decimal('0.00')`` directly (mirrors the §12.J prose
        "(mocked)" wording).

        Same exception path; this test isolates the §12 service-layer
        D1 check from §9 internals — if §9's surface contract ever
        widens (e.g., starts returning ``None`` for missing in V1.5),
        the mocked variant remains representative of the §12 D1 contract
        independently."""
        from app.modules.category import service as category_service

        async def _stub_zero(category_id, *args, **kwargs):
            return Decimal("0.00")

        monkeypatch.setattr(category_service, "get_commission", _stub_zero)

        request = PriceCalcRequest(
            input_cost=Decimal("100"),
            target_margin_pct=Decimal("30"),
        )

        with pytest.raises(CommissionMissingError):
            await pricing_service.calculate(
                user_id=user.id,
                product_id=product_row.id,
                request=request,
                db=db,
            )

    async def test_commission_missing_does_not_persist_calc(
        self, db, user, product_uncommissioned, use_live_valkey
    ):
        """When :class:`CommissionMissingError` raises, NO row is
        inserted into ``pricing_calcs`` (the §12.B.1 step 5 fail-fast
        path short-circuits before step 8 persistence)."""
        from sqlalchemy import select
        from app.shared.models.pricing_calc import PricingCalc as PricingCalcORM

        request = PriceCalcRequest(
            input_cost=Decimal("100"),
            target_margin_pct=Decimal("30"),
        )

        with pytest.raises(CommissionMissingError):
            await pricing_service.calculate(
                user_id=user.id,
                product_id=product_uncommissioned.id,
                request=request,
                db=db,
            )

        # No pricing_calcs row should exist for this product.
        result = await db.execute(
            select(PricingCalcORM).where(
                PricingCalcORM.product_id == product_uncommissioned.id
            )
        )
        rows = result.scalars().all()
        assert rows == [], (
            f"CommissionMissingError must short-circuit BEFORE persistence; "
            f"found {len(rows)} unexpected pricing_calcs row(s)"
        )
