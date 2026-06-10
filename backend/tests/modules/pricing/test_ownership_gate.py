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


pytestmark = pytest.mark.asyncio


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
            input_cost=Decimal("100"),
            target_margin_pct=Decimal("30"),
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
            input_cost=Decimal("100"),
            target_margin_pct=Decimal("30"),
        )

        # We expect this to succeed — but the service does I/O against
        # category.get_commission which uses cache helpers.  This test
        # only asserts that the ownership-gate exception is NOT raised.
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

        # If we got a response, at least confirm the shape is sane.
        assert response.commission_pct == Decimal("15.00"), (
            "priced_category seeds commission_pct=15.00; pricing should "
            f"echo it on the response — got {response.commission_pct}"
        )

    async def test_nonexistent_product_raises_product_not_found(
        self, db, user, priced_category, use_live_valkey
    ):
        """A product UUID that doesn't exist at all also raises
        :class:`ProductNotFoundError` — same envelope as cross-tenant
        (the §10 leak-protection invariant)."""
        import uuid

        request = PriceCalcRequest(
            input_cost=Decimal("100"),
            target_margin_pct=Decimal("30"),
        )

        with pytest.raises(ProductNotFoundError):
            await pricing_service.calculate(
                user_id=user.id,
                product_id=uuid.uuid4(),
                request=request,
                db=db,
            )
