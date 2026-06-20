"""Pricing-module unit test — Ownership gate.

Per BACKEND_ARCHITECTURE.md §12.J as superseded by the **W2 Price Calculator
rework (census-confirmed settlement model, 2026-06-19)**.

Cross-tenant product access raises :class:`ProductNotFoundError` (404) from the
§10.C ``assert_product_ownership`` gate.  Verified at the service layer
(calling :func:`pricing.service.calculate` directly); the router test suite
verifies the 404 HTTP mapping via the §4.F error handler.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.catalog.exceptions import ProductNotFoundError
from app.modules.pricing import service as pricing_service
from app.modules.pricing.schemas import PriceCalcRequest


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


class TestOwnershipGate:
    """Cross-tenant product access raises ProductNotFoundError."""

    async def test_cross_tenant_product_raises_product_not_found(
        self, db, user, other_user_product, use_live_valkey
    ):
        """``user`` calls price-calc on ``other_user_product`` →
        :class:`ProductNotFoundError`.

        The exception is sourced from
        :func:`catalog.service.assert_product_ownership` per §10.C
        leak-protection rule — the API does NOT distinguish "no such
        product" from "exists but owned by someone else".
        """
        request = PriceCalcRequest(selling_price=Decimal("500"))

        with pytest.raises(ProductNotFoundError):
            await pricing_service.calculate(
                user_id=user.id,
                product_id=other_user_product.id,
                request=request,
                db=db,
            )

    async def test_nonexistent_product_raises_product_not_found(
        self, db, user, use_live_valkey
    ):
        """A product UUID that doesn't exist also raises
        :class:`ProductNotFoundError` — same envelope as cross-tenant
        (the §10 leak-protection invariant).
        """
        import uuid

        request = PriceCalcRequest(selling_price=Decimal("500"))

        with pytest.raises(ProductNotFoundError):
            await pricing_service.calculate(
                user_id=user.id,
                product_id=uuid.uuid4(),
                request=request,
                db=db,
            )
