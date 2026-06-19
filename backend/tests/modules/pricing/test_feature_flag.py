"""Unit tests — FEATURE_PRICE_CALCULATOR_ENABLED flag guard + router-level
contracts (unknown-category 422, negative-settlement 200 alert).

Session: mesell-flag-parity-sweep-session-1 + W2c api-routes-builder
Per FEATURE_PLAN.md §1.B D2 + Master Plan §3.2 backend feature-flag protocol.
Per W2_BACKEND_SPEC.md §2.3 router error mapping.

Test inventory
--------------
1. ``test_price_calc_returns_404_when_flag_disabled`` — POST returns 404 when
   FEATURE_PRICE_CALCULATOR_ENABLED=False.
2. ``test_price_calc_flag_off_404_body_is_json`` — body is valid JSON.
3. ``test_price_calc_route_reachable_when_flag_enabled`` — does NOT return the
   flag-guard 404 when flag is True (default).
4. ``test_unknown_category_is_422_not_500`` — router maps UnknownCategoryError
   to 422 ``pricing.category.no_pricing_data`` (W2 addition).
5. ``test_negative_settlement_returns_200_with_alert`` — selling_price tiny vs
   shipping → HTTP 200 + NEGATIVE_SETTLEMENT alert (service mocked).

Fixture strategy
----------------
- ``stub_pricing_client`` creates an in-process ASGI client with stub
  ``get_current_user`` override (no real JWT/DB user record needed).
- Tests 4 & 5 also stub the service to control the failure mode / return value,
  removing DB dependency from router-level unit tests.

Markers: ``unit`` (no real I/O).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.auth import CurrentUser, get_current_user
from app.main import app
from app.modules.pricing.pricing_lookup import UnknownCategoryError
from app.modules.pricing.schemas import PriceCalcAlert, PriceCalcResponse

# ── Stub identifiers ──────────────────────────────────────────────────────────

_STUB_USER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000cc")
_STUB_PLAN: str = "free"
_STUB_PRODUCT_ID = uuid.UUID("00000000-0000-0000-0000-000000000033")

# Minimal valid W2 request body.
_VALID_REQUEST_BODY: dict[str, Any] = {"selling_price": "500.00"}


def _make_stub_user() -> CurrentUser:
    @dataclass(frozen=True)
    class _StubCurrentUser:
        user_id: uuid.UUID = _STUB_USER_ID
        plan: str = _STUB_PLAN

    return _StubCurrentUser()  # type: ignore[return-value]


async def _stub_get_current_user() -> CurrentUser:
    return _make_stub_user()  # type: ignore[return-value]


# ── Fixture ───────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(loop_scope="function")
async def stub_pricing_client(use_live_valkey):
    """ASGI client with stub auth override.

    Only ``get_current_user`` is overridden.  The flag-guard + router-level
    tests fire BEFORE (or instead of) any DB call, so DB override is not
    required for these assertions.

    Depends on ``use_live_valkey`` to reset Valkey singletons per function —
    the ``@rate_limit`` / ``@audit_event`` decorators touch Valkey even on the
    404 short-circuit path; a singleton bound to a prior loop raises
    "Event loop is closed" on the second test.
    """
    app.dependency_overrides[get_current_user] = _stub_get_current_user
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


# ── Test 1: 404 on POST when flag disabled ────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_price_calc_returns_404_when_flag_disabled(stub_pricing_client):
    """FEATURE_PRICE_CALCULATOR_ENABLED=False → POST returns 404 with the
    locked detail string.

    Request body uses the W2 field name ``selling_price`` (NOT the retired
    #285 ``meesho_price``).
    """
    with patch("app.modules.pricing.router.settings") as mock_settings:
        mock_settings.FEATURE_PRICE_CALCULATOR_ENABLED = False

        response = await stub_pricing_client.post(
            f"/api/v1/products/{_STUB_PRODUCT_ID}/price-calc",
            json=_VALID_REQUEST_BODY,
        )

    assert response.status_code == 404, (
        f"Expected 404 when flag is disabled, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body.get("detail") == "Price Calculator is disabled in this environment", (
        f"Unexpected detail: {body.get('detail')!r}"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_price_calc_flag_off_404_body_is_json(stub_pricing_client):
    """Flag-disabled 404 response carries a valid JSON body."""
    with patch("app.modules.pricing.router.settings") as mock_settings:
        mock_settings.FEATURE_PRICE_CALCULATOR_ENABLED = False

        response = await stub_pricing_client.post(
            f"/api/v1/products/{_STUB_PRODUCT_ID}/price-calc",
            json=_VALID_REQUEST_BODY,
        )

    assert response.status_code == 404
    body = response.json()
    assert isinstance(body, dict)
    assert "detail" in body


# ── Test 2: POST route reachable when flag enabled ────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_price_calc_route_reachable_when_flag_enabled(stub_pricing_client):
    """FEATURE_PRICE_CALCULATOR_ENABLED=True (default) → POST does NOT return
    the flag-guard 404.

    The response may be any status except the guard-specific 404 detail.
    Infra-down 500 is accepted (skip).
    """
    response = await stub_pricing_client.post(
        f"/api/v1/products/{_STUB_PRODUCT_ID}/price-calc",
        json=_VALID_REQUEST_BODY,
    )

    if response.status_code == 404:
        body = response.json()
        assert (
            body.get("detail") != "Price Calculator is disabled in this environment"
        ), (
            "Flag guard fired even though FEATURE_PRICE_CALCULATOR_ENABLED=True. "
            f"Full response: {body}"
        )
        return  # real 404 from service (product not found) is acceptable

    if response.status_code == 500:
        body_text = response.text
        if any(
            kw in body_text
            for kw in ("Connection refused", "could not connect", "asyncpg")
        ):
            pytest.skip("DB infra not available — flag-guard path (test 1) is authoritative")

    assert response.status_code in {200, 400, 404, 422, 500}, (
        f"Unexpected status {response.status_code}: {response.text}"
    )


# ── Test 3: UnknownCategoryError → 422 not 500 ───────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unknown_category_is_422_not_500(stub_pricing_client):
    """Router maps UnknownCategoryError → 422 pricing.category.no_pricing_data.

    Stubs ``pricing.service.calculate`` to raise ``UnknownCategoryError``
    (as it would when the product's meesho_leaf_id is absent from the lookup),
    then asserts the router translates it to a clean 422 with the correct
    error code — NOT a 500.

    This is the critical W2 addition: the service lets UnknownCategoryError
    bubble; the router catches it and re-raises CategoryPricingUnavailableError
    which goes through _meesell_error_handler → 422 + locked envelope.
    """
    with patch(
        "app.modules.pricing.service.calculate",
        new_callable=AsyncMock,
        side_effect=UnknownCategoryError(
            "meesho_leaf_id '99999' not found in pricing lookup"
        ),
    ):
        response = await stub_pricing_client.post(
            f"/api/v1/products/{_STUB_PRODUCT_ID}/price-calc",
            json=_VALID_REQUEST_BODY,
        )

    assert response.status_code == 422, (
        f"Expected 422 for unknown category, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body.get("code") == "pricing.category.no_pricing_data", (
        f"Expected code='pricing.category.no_pricing_data', got {body.get('code')!r}"
    )


# ── Test 4: negative settlement → 200 + NEGATIVE_SETTLEMENT alert ─────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_negative_settlement_returns_200_with_alert(stub_pricing_client):
    """A negative estimated_bank_settlement returns HTTP 200 + one alert.

    Stubs ``pricing.service.calculate`` to return a pre-built response with
    a negative ``estimated_bank_settlement`` and one NEGATIVE_SETTLEMENT alert.
    Asserts that the router does NOT reject/remap this to 400 or 422 — it
    must pass through as 200 per the locked spec.
    """
    stub_response = PriceCalcResponse(
        selling_price=Decimal("1.00"),
        shipping=Decimal("8435.00"),
        total_price=Decimal("8436.00"),
        commission_pct=Decimal("0.00"),
        commission_fees=Decimal("0.00"),
        gst_on_shipping=Decimal("1518.30"),
        tds=Decimal("8.44"),
        tcs=Decimal("0.00"),
        estimated_bank_settlement=Decimal("-1525.74"),
        alerts=[
            PriceCalcAlert(
                code="NEGATIVE_SETTLEMENT",
                message_id="pricing.alert.negative_settlement",
                severity="warning",
            )
        ],
        calculated_at=datetime.now(timezone.utc),
    )

    with patch(
        "app.modules.pricing.service.calculate",
        new_callable=AsyncMock,
        return_value=stub_response,
    ):
        response = await stub_pricing_client.post(
            f"/api/v1/products/{_STUB_PRODUCT_ID}/price-calc",
            json=_VALID_REQUEST_BODY,
        )

    assert response.status_code == 200, (
        f"Negative settlement must be 200 (not a 400/422), "
        f"got {response.status_code}: {response.text}"
    )
    body = response.json()
    # The headline output is negative.
    settlement = Decimal(body["estimated_bank_settlement"])
    assert settlement < Decimal("0"), (
        f"Expected negative settlement in response, got {settlement}"
    )
    # Exactly one alert with code NEGATIVE_SETTLEMENT.
    alerts = body.get("alerts", [])
    assert len(alerts) == 1, f"Expected 1 alert, got {len(alerts)}: {alerts}"
    assert alerts[0]["code"] == "NEGATIVE_SETTLEMENT"
    assert alerts[0]["severity"] == "warning"


# ── Test 5: old field names rejected (extra=forbid) ───────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_old_285_request_fields_rejected_with_422(stub_pricing_client):
    """Sending the retired #285 field ``meesho_price`` (or ``input_cost``)
    must return 422 because ``PriceCalcRequest`` has ``extra="forbid"``.

    This is the W3 coordination gate: the FE must ship the new body
    (``selling_price``) in lockstep with W2 merging to develop.  A stale FE
    sending the old fields gets a predictable 422, not a silent wrong answer.
    """
    with patch("app.modules.pricing.router.settings") as mock_settings:
        mock_settings.FEATURE_PRICE_CALCULATOR_ENABLED = True

        response = await stub_pricing_client.post(
            f"/api/v1/products/{_STUB_PRODUCT_ID}/price-calc",
            json={"meesho_price": "500.00", "input_cost": "100.00"},
        )

    assert response.status_code == 422, (
        f"Extra fields (meesho_price, input_cost) should be rejected with 422 "
        f"(extra=forbid), got {response.status_code}: {response.text}"
    )
