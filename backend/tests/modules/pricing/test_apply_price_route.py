"""PQE Wave A — apply-price route + offline guarantee + get_last_calc.

Covers:
  PQE-BE-09  commission override at 5% reduces settlement by exactly 5%×sp
  PQE-BE-15  POST /apply-price → 204 (route boundary, no body)
  PQE-BE-16  apply-price NEVER writes mrp / status=None (service unit)
  PQE-BE-17  apply-price selling_price ≤ 0 → rejected (service + route)
  PQE-BE-18  apply-price cross-tenant → 404
  PQE-BE-19  apply-price flag-OFF → 404
  PQE-BE-20  get_last_calc: None before any calc, latest row after
  PQE-BE-21  OFFLINE hard rule: no httpx / Meesho client in pricing path

All stub-only (no live DB).  Markers: ``unit``.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.auth import CurrentUser, get_current_user
from app.main import app
from app.modules.catalog.exceptions import ProductNotFoundError
from app.modules.pricing import service as pricing_service
from app.modules.pricing.exceptions import InvalidPriceInputError
from app.modules.pricing.service import _compute_settlement

pytestmark = pytest.mark.unit

# ── Stub identifiers ──────────────────────────────────────────────────────────
_STUB_USER_ID = UUID("00000000-0000-0000-0000-0000000000dd")
_STUB_PLAN = "free"
_STUB_PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000044")


def _make_stub_user() -> CurrentUser:
    @dataclass(frozen=True)
    class _Stub:
        user_id: UUID = _STUB_USER_ID
        plan: str = _STUB_PLAN

    return _Stub()  # type: ignore[return-value]


async def _stub_get_current_user() -> CurrentUser:
    return _make_stub_user()  # type: ignore[return-value]


@pytest_asyncio.fixture(loop_scope="function")
async def stub_apply_client(use_live_valkey):
    """ASGI client with stub auth for apply-price route tests (no real DB).

    ``use_live_valkey`` resets Valkey singletons per-function so that the
    rate_limit / audit_event decorators do not raise 'Event loop is closed'
    on the second test.  This mirrors the pattern in test_feature_flag.py.
    """
    app.dependency_overrides[get_current_user] = _stub_get_current_user
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


# ─────────────────────────────────────────────────────────────────────────────
# PQE-BE-09  commission override: 5% commission reduces settlement by 5%×sp
# ─────────────────────────────────────────────────────────────────────────────
def test_pqe_be_09_commission_override_5pct():
    """5% commission override reduces settlement by exactly 5%×selling_price.

    Arrange: selling_price=200, shipping=45; compute at 0% and 5%.
    Act: compare the two results.
    Assert: commission_fees==10.00; settlement difference==10.00.
    """
    with_comm = _compute_settlement(
        selling_price=Decimal("200"),
        shipping=45,
        commission_pct=Decimal("5"),
    )
    without_comm = _compute_settlement(
        selling_price=Decimal("200"),
        shipping=45,
        commission_pct=Decimal("0"),
    )

    assert with_comm.commission_fees == Decimal("10.00"), (
        f"5% of 200 should be commission_fees=10.00, got {with_comm.commission_fees}"
    )
    assert (
        without_comm.estimated_bank_settlement - with_comm.estimated_bank_settlement
        == Decimal("10.00")
    ), "commission override must reduce settlement by exactly commission_fees"


# ─────────────────────────────────────────────────────────────────────────────
# PQE-BE-15  POST /apply-price route → 204 (happy path)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_pqe_be_15_apply_price_route_returns_204(stub_apply_client):
    """POST /apply-price with a valid selling_price → 204 No Content.

    Arrange: stub apply_price_to_product to return None (success).
    Act: POST /products/{id}/apply-price selling_price=150.
    Assert: status 204; empty body.
    """
    with patch(
        "app.modules.pricing.service.apply_price_to_product",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await stub_apply_client.post(
            f"/api/v1/products/{_STUB_PRODUCT_ID}/apply-price",
            json={"selling_price": "150.00"},
        )

    assert resp.status_code == 204, (
        f"Expected 204 No Content, got {resp.status_code}: {resp.text}"
    )
    assert resp.content == b"", (
        f"204 must carry no body, got {resp.content!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PQE-BE-16  apply-price NEVER writes mrp or changes status
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_pqe_be_16_apply_price_never_writes_mrp_or_status(monkeypatch):
    """apply_price_to_product writes ONLY meesho_price; status is always None.

    Arrange: spy on catalog_service.patch_product.
    Act: call apply_price_to_product(selling_price=250).
    Assert: fields carries 'meesho_price' and NOT 'mrp'; status is None.
    """
    spy = AsyncMock(return_value=None)
    monkeypatch.setattr(pricing_service.catalog_service, "patch_product", spy)

    await pricing_service.apply_price_to_product(
        _STUB_USER_ID,
        _STUB_PRODUCT_ID,
        Decimal("250.00"),
        db="SENTINEL_DB",
    )

    spy.assert_awaited_once()
    patch_request = spy.call_args.args[2]  # positional: (user_id, product_id, patch_req, ...)

    assert "meesho_price" in patch_request.fields, (
        "apply_price must write meesho_price into fields"
    )
    assert "mrp" not in patch_request.fields, (
        "apply_price must NOT touch mrp — that is a separate product decision"
    )
    assert patch_request.status is None, (
        f"apply_price must never mutate status; got {patch_request.status!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PQE-BE-17  apply-price selling_price ≤ 0 → rejected before catalog
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_pqe_be_17_service_rejects_zero_price(monkeypatch):
    """selling_price=0 raises InvalidPriceInputError before catalog is called."""
    spy = AsyncMock(return_value=None)
    monkeypatch.setattr(pricing_service.catalog_service, "patch_product", spy)

    with pytest.raises(InvalidPriceInputError):
        await pricing_service.apply_price_to_product(
            _STUB_USER_ID,
            _STUB_PRODUCT_ID,
            Decimal("0"),
            db="SENTINEL_DB",
        )

    spy.assert_not_awaited()


@pytest.mark.asyncio
async def test_pqe_be_17_service_rejects_negative_price(monkeypatch):
    """selling_price=-1 raises InvalidPriceInputError before catalog is called."""
    spy = AsyncMock(return_value=None)
    monkeypatch.setattr(pricing_service.catalog_service, "patch_product", spy)

    with pytest.raises(InvalidPriceInputError):
        await pricing_service.apply_price_to_product(
            _STUB_USER_ID,
            _STUB_PRODUCT_ID,
            Decimal("-1"),
            db="SENTINEL_DB",
        )

    spy.assert_not_awaited()


@pytest.mark.asyncio
async def test_pqe_be_17_route_rejects_zero_selling_price(stub_apply_client):
    """POST /apply-price with selling_price=0 → 422 (Pydantic gt=0 enforcement)."""
    resp = await stub_apply_client.post(
        f"/api/v1/products/{_STUB_PRODUCT_ID}/apply-price",
        json={"selling_price": "0"},
    )
    assert resp.status_code == 422, (
        f"Expected 422 for selling_price=0, got {resp.status_code}: {resp.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PQE-BE-18  apply-price cross-tenant → 404
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_pqe_be_18_apply_price_cross_tenant_404(stub_apply_client):
    """apply_price_to_product raises ProductNotFoundError from catalog gate → 404.

    The router must translate the catalog ownership error to a 404 (no info-leak).
    """
    with patch(
        "app.modules.pricing.service.apply_price_to_product",
        new_callable=AsyncMock,
        side_effect=ProductNotFoundError(),
    ):
        resp = await stub_apply_client.post(
            f"/api/v1/products/{_STUB_PRODUCT_ID}/apply-price",
            json={"selling_price": "100.00"},
        )

    assert resp.status_code == 404, (
        f"Cross-tenant apply-price must return 404, got {resp.status_code}: {resp.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PQE-BE-19  apply-price flag-OFF → 404
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_pqe_be_19_apply_price_flag_off_returns_404(stub_apply_client):
    """FEATURE_PRICE_CALCULATOR_ENABLED=False → POST /apply-price returns 404.

    Both price-calc and apply-price share the same feature flag gate in the router.
    """
    with patch("app.modules.pricing.router.settings") as mock_settings:
        mock_settings.FEATURE_PRICE_CALCULATOR_ENABLED = False
        resp = await stub_apply_client.post(
            f"/api/v1/products/{_STUB_PRODUCT_ID}/apply-price",
            json={"selling_price": "100.00"},
        )

    assert resp.status_code == 404, (
        f"apply-price with flag disabled must return 404, "
        f"got {resp.status_code}: {resp.text}"
    )
    assert resp.json().get("detail") == "Price Calculator is disabled in this environment"


# ─────────────────────────────────────────────────────────────────────────────
# PQE-BE-20  get_last_calc: None before any calc, row after
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_pqe_be_20_get_last_calc_none_before_calc(monkeypatch):
    """get_last_calc returns None when no pricing_calcs row exists.

    Arrange: stub assert_product_ownership (no-op) + find_latest_by_product (None).
    Act: call get_last_calc.
    Assert: returns None.
    """
    monkeypatch.setattr(
        pricing_service.catalog_service,
        "assert_product_ownership",
        AsyncMock(return_value=None),
    )
    from app.modules.pricing import repository as pricing_repo

    monkeypatch.setattr(
        pricing_repo,
        "find_latest_by_product",
        AsyncMock(return_value=None),
    )

    result = await pricing_service.get_last_calc(
        user_id=_STUB_USER_ID,
        product_id=_STUB_PRODUCT_ID,
        db="SENTINEL_DB",
    )
    assert result is None


@pytest.mark.asyncio
async def test_pqe_be_20_get_last_calc_returns_row_after_calc(monkeypatch):
    """get_last_calc returns the most recent PricingCalc row after a calc.

    Arrange: stub find_latest_by_product to return a sentinel object.
    Act: call get_last_calc.
    Assert: result is the sentinel row (ownership check also called).
    """
    sentinel_row = MagicMock(name="pricing_calc_row")

    monkeypatch.setattr(
        pricing_service.catalog_service,
        "assert_product_ownership",
        AsyncMock(return_value=None),
    )
    from app.modules.pricing import repository as pricing_repo

    monkeypatch.setattr(
        pricing_repo,
        "find_latest_by_product",
        AsyncMock(return_value=sentinel_row),
    )

    result = await pricing_service.get_last_calc(
        user_id=_STUB_USER_ID,
        product_id=_STUB_PRODUCT_ID,
        db="SENTINEL_DB",
    )
    assert result is sentinel_row


# ─────────────────────────────────────────────────────────────────────────────
# PQE-BE-21  OFFLINE hard rule: no httpx / Meesho client in pricing path
# ─────────────────────────────────────────────────────────────────────────────
def test_pqe_be_21_pricing_service_has_no_http_import():
    """pricing.service must NOT import httpx, requests, or aiohttp.

    The calculator is fully OFFLINE — pure arithmetic over a static JSON file.
    No live Meesho/supplier HTTP call is ever made.

    Arrange: force-import the pricing service module.
    Assert: forbidden HTTP libraries not found in the module's source text.
    """
    import inspect

    import app.modules.pricing.service as svc

    source = inspect.getsource(svc)
    for forbidden in ("httpx", "requests", "aiohttp", "urllib.request"):
        assert forbidden not in source, (
            f"pricing.service source contains '{forbidden}' — violates OFFLINE "
            "hard rule. The calculator must never make real HTTP calls."
        )


def test_pqe_be_21_pricing_lookup_has_no_http_import():
    """pricing_lookup.py must NOT import httpx, requests, or aiohttp.

    The lookup reads a local JSON file via stdlib only.
    """
    import inspect

    import app.modules.pricing.pricing_lookup as plookup

    source = inspect.getsource(plookup)
    for forbidden in ("httpx", "requests", "aiohttp"):
        assert forbidden not in source, (
            f"pricing_lookup source contains '{forbidden}' — must be stdlib + decimal only."
        )
    # Confirm the offline API is still callable (basic smoke).
    assert callable(plookup.get_shipping)
    assert callable(plookup.get_commission_default)
    assert callable(plookup.lookup_size)
