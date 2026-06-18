"""Pricing-module unit test #1 — Ownership gate.

Per BACKEND_ARCHITECTURE.md §12.J:

    Ownership gate — ``POST /products/{other_user_product}/price-calc``
    → 404 ``catalog.product_not_found``.  Validates the §10.C
    cross-module gate consumption.

This is exercised at the service layer (calling
:func:`pricing.service.calculate` directly with a cross-tenant
``product_id``) — the route is a thin wrapper that forwards to the
service, so a service-level assertion is sufficient to lock the
contract.  The 404 status mapping is verified by the §4.F error-handler
test suite + the catalog ownership test.
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
        product" from "exists but owned by someone else"."""
        request = PriceCalcRequest(
            meesho_price=Decimal("500"),
            input_cost=Decimal("100"),
        )

        with pytest.raises(ProductNotFoundError):
            await pricing_service.calculate(
                user_id=user.id,
                product_id=other_user_product.id,
                request=request,
                db=db,
            )

    async def test_owned_product_does_not_raise_ownership_error(
        self, db, user, product_row, use_live_valkey
    ):
        """Sanity counter-test — when the same user owns the product,
        the ownership gate passes (and the calc completes; verified by
        the integration tests, not asserted here)."""
        request = PriceCalcRequest(
            meesho_price=Decimal("500"),
            input_cost=Decimal("100"),
        )

        # We expect this to succeed.  Per §12.M commission is a seller
        # input (default 4%), NOT a category lookup — the calc is pure
        # arithmetic after the ownership gate.  This test only asserts the
        # ownership-gate exception is NOT raised.
        try:
            response = await pricing_service.calculate(
                user_id=user.id,
                product_id=product_row.id,
                request=request,
                db=db,
            )
        except ProductNotFoundError as exc:
            pytest.fail(
                f"ownership-gate falsely raised for owned product: {exc}"
            )

        # If we got a response, confirm the seller-input commission default
        # (4%) is echoed — proving the §12.M commission-as-input contract.
        assert response.commission_pct == Decimal("4.00"), (
            "§12.M: commission defaults to the seller-input 4% — pricing "
            f"should echo it on the response — got {response.commission_pct}"
        )

    async def test_nonexistent_product_raises_product_not_found(
        self, db, user, priced_category, use_live_valkey
    ):
        """A product UUID that doesn't exist at all also raises
        :class:`ProductNotFoundError` — same envelope as cross-tenant
        (the §10 leak-protection invariant)."""
        import uuid

        request = PriceCalcRequest(
            meesho_price=Decimal("500"),
            input_cost=Decimal("100"),
        )

        with pytest.raises(ProductNotFoundError):
            await pricing_service.calculate(
                user_id=user.id,
                product_id=uuid.uuid4(),
                request=request,
                db=db,
            )
