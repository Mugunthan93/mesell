"""Unit tests for ``pricing.service.apply_price_to_product`` (W4 — explicit
"apply chosen price to product" action).

The method is the single link that lands the calculator's CHOSEN selling price
into ``products.fields_jsonb`` (under the Meesho price canonical) so it flows to
the XLSX export — which already emits any canonical present in ``fields_jsonb``.

These are DB-free: ``catalog.service.patch_product`` (the reused §10.B.2 write
seam carrying ownership + per-field schema validation + the atomic JSONB merge)
is mocked.  We assert THIS method's contract:

* it writes the chosen price under :data:`SELLING_PRICE_CANONICAL`
  (``meesho_price``) and ONLY that canonical (never ``mrp``);
* it rejects a non-positive price BEFORE touching catalog;
* ownership / validation failures bubble verbatim from ``patch_product``;
* it never auto-mutates ``status`` (always ``None``).
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.modules.pricing import service as pricing_service
from app.modules.pricing.exceptions import InvalidPriceInputError

pytestmark = pytest.mark.unit


_USER_ID = uuid4()
_PRODUCT_ID = uuid4()


@pytest.fixture
def patch_product_spy(monkeypatch) -> AsyncMock:
    """Replace ``catalog_service.patch_product`` with an AsyncMock so the
    test runs with no DB and we can inspect the exact call."""
    spy = AsyncMock(return_value=None)
    monkeypatch.setattr(
        pricing_service.catalog_service, "patch_product", spy
    )
    return spy


# ── Happy path — writes the value into fields_jsonb via patch_product ────────
@pytest.mark.asyncio
async def test_apply_writes_selling_price_under_meesho_price_canonical(
    patch_product_spy: AsyncMock,
) -> None:
    await pricing_service.apply_price_to_product(
        _USER_ID,
        _PRODUCT_ID,
        Decimal("106.00"),
        db="SENTINEL_DB",
    )

    patch_product_spy.assert_awaited_once()
    args, kwargs = patch_product_spy.call_args

    # user_id + product_id forwarded positionally (M6 tenancy gate).
    assert args[0] == _USER_ID
    assert args[1] == _PRODUCT_ID

    # The request shim carries the price under the SELLING price canonical.
    request = args[2]
    assert request.fields == {
        pricing_service.SELLING_PRICE_CANONICAL: Decimal("106.00")
    }
    assert pricing_service.SELLING_PRICE_CANONICAL == "meesho_price"

    # Applying a price NEVER changes the draft/ready state.
    assert request.status is None

    # Explicit, audited write — not a coalesced autosave draft.
    assert kwargs["is_autosave"] is False
    assert kwargs["db"] == "SENTINEL_DB"


@pytest.mark.asyncio
async def test_apply_writes_only_meesho_price_never_mrp(
    patch_product_spy: AsyncMock,
) -> None:
    """The calculator produces ONE seller-chosen number → ``mrp`` (the
    strike-through MRP) must be left untouched (open-question flag)."""
    await pricing_service.apply_price_to_product(
        _USER_ID, _PRODUCT_ID, Decimal("499.00"), db=object()
    )

    request = patch_product_spy.call_args.args[2]
    assert set(request.fields) == {"meesho_price"}
    assert "mrp" not in request.fields


@pytest.mark.asyncio
async def test_apply_quantizes_to_two_places(
    patch_product_spy: AsyncMock,
) -> None:
    """A price with extra precision is quantized to 2 dp (ROUND_HALF_UP)
    before the merge so the stored value matches the wire money convention."""
    await pricing_service.apply_price_to_product(
        _USER_ID, _PRODUCT_ID, Decimal("106.005"), db=object()
    )

    stored = patch_product_spy.call_args.args[2].fields["meesho_price"]
    assert stored == Decimal("106.01")


# ── Invalid price rejected BEFORE any catalog call ──────────────────────────
@pytest.mark.parametrize("bad_price", [Decimal("0"), Decimal("-1"), Decimal("-0.01")])
@pytest.mark.asyncio
async def test_apply_rejects_non_positive_price(
    patch_product_spy: AsyncMock, bad_price: Decimal
) -> None:
    with pytest.raises(InvalidPriceInputError):
        await pricing_service.apply_price_to_product(
            _USER_ID, _PRODUCT_ID, bad_price, db=object()
        )

    # The product is never touched when the price is invalid.
    patch_product_spy.assert_not_awaited()


# ── Ownership / validation failures bubble verbatim ─────────────────────────
@pytest.mark.asyncio
async def test_apply_propagates_ownership_failure(monkeypatch) -> None:
    """A cross-tenant / missing / soft-deleted product surfaces as the
    catalog ProductNotFoundError raised inside patch_product (the M6 gate)."""
    from app.modules.catalog.exceptions import ProductNotFoundError

    failing = AsyncMock(side_effect=ProductNotFoundError())
    monkeypatch.setattr(
        pricing_service.catalog_service, "patch_product", failing
    )

    with pytest.raises(ProductNotFoundError):
        await pricing_service.apply_price_to_product(
            _USER_ID, _PRODUCT_ID, Decimal("106.00"), db=object()
        )


@pytest.mark.asyncio
async def test_apply_propagates_schema_validation_failure(monkeypatch) -> None:
    """A value that fails the catalog schema range/enum check for
    ``meesho_price`` bubbles the 422 ValidationFailedError verbatim — the
    method does NOT swallow or remap it."""
    from app.modules.catalog.exceptions import ValidationFailedError

    failing = AsyncMock(
        side_effect=ValidationFailedError(
            validation_message_id="validation.meesho_price.out_of_range",
            detail="out of range",
        )
    )
    monkeypatch.setattr(
        pricing_service.catalog_service, "patch_product", failing
    )

    with pytest.raises(ValidationFailedError):
        await pricing_service.apply_price_to_product(
            _USER_ID, _PRODUCT_ID, Decimal("999999.00"), db=object()
        )
