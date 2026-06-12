"""Unit tests — FEATURE_PRICE_CALCULATOR_ENABLED flag guard.

Session: mesell-flag-parity-sweep-session-1
Per FEATURE_PLAN.md §1.B D2 + Master Plan §3.2 backend feature-flag protocol.

Two test paths covered
----------------------
1. **404-when-disabled** (``FEATURE_PRICE_CALCULATOR_ENABLED=False``):
   POST /api/v1/products/{id}/price-calc returns
   ``{"detail": "Price Calculator is disabled in this environment"}`` with
   HTTP 404 regardless of request content.
   This path is fully self-contained — no DB or Valkey required.

2. **Route-reachable when enabled** (``FEATURE_PRICE_CALCULATOR_ENABLED=True``,
   the default):
   POST /api/v1/products/{id}/price-calc is reachable (does NOT return the
   flag-guard 404) when the flag is on.  Full end-to-end response is
   infra-gated (dev-tunnel DB + categories seed required).  When infra is
   unavailable the test confirms a non-flag-guard response (anything except
   the 404 the flag guard emits) so the gate is meaningful in CI without
   a live DB.

Fixture strategy
----------------
- ``stub_pricing_client`` creates an in-process ASGI client with a single
  dependency override:
    * ``get_current_user`` → a stub that returns a synthetic ``CurrentUser``
      so no valid JWT or DB user record is required.
- For the 404 path, ``get_db`` override is irrelevant — the flag guard fires
  before the service call, so the DB is never touched.
- ``settings.FEATURE_PRICE_CALCULATOR_ENABLED`` is patched at the router
  import surface via ``unittest.mock.patch`` — specifically
  ``app.modules.pricing.router.settings`` (the module-level name in the
  router, NOT ``app.shared.config.settings``) per the smart-picker +
  export precedent. This makes the patch active only within the
  ``with patch(...)`` block and is automatically restored on exit.

Markers: ``unit`` (no I/O — flag guard fires before any DB or service call).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.auth import CurrentUser, get_current_user
from app.main import app

# ── Stub user ─────────────────────────────────────────────────────────────────

_STUB_USER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000cc")
_STUB_PLAN: str = "free"

# A random product UUID used as the path param in all price-calc POST requests.
_STUB_PRODUCT_ID = uuid.UUID("00000000-0000-0000-0000-000000000033")


def _make_stub_user() -> CurrentUser:
    """Synthetic CurrentUser — satisfies the Depends(get_current_user) type."""

    @dataclass(frozen=True)
    class _StubCurrentUser:
        user_id: uuid.UUID = _STUB_USER_ID
        plan: str = _STUB_PLAN

    return _StubCurrentUser()  # type: ignore[return-value]


async def _stub_get_current_user() -> CurrentUser:
    return _make_stub_user()  # type: ignore[return-value]


# ── Fixture — lightweight ASGI client with stub auth ─────────────────────────


@pytest_asyncio.fixture(loop_scope="function")
async def stub_pricing_client():
    """ASGI client with stub auth override; NO DB/Valkey required.

    Only ``get_current_user`` is overridden — the DB override is left out
    intentionally.  The flag-guard tests fire BEFORE any DB call, so DB
    access is irrelevant for the flag-disabled assertions.
    """
    app.dependency_overrides[get_current_user] = _stub_get_current_user
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        async with app.router.lifespan_context(app):
            yield ac
    app.dependency_overrides.pop(get_current_user, None)


# ── Test 1: 404 on POST when flag disabled ────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_price_calc_returns_404_when_flag_disabled(stub_pricing_client):
    """FEATURE_PRICE_CALCULATOR_ENABLED=False → POST returns 404 with locked detail.

    Patches ``app.modules.pricing.router.settings`` at the module level so
    the guard expression ``if not settings.FEATURE_PRICE_CALCULATOR_ENABLED``
    evaluates True.  Auth is stubbed so the dependency chain resolves without
    a real JWT.

    Acceptance criteria (FEATURE_PLAN.md §1.B D2 + Master Plan §3.2):
    - HTTP 404
    - body["detail"] == "Price Calculator is disabled in this environment"
    """
    with patch("app.modules.pricing.router.settings") as mock_settings:
        mock_settings.FEATURE_PRICE_CALCULATOR_ENABLED = False

        response = await stub_pricing_client.post(
            f"/api/v1/products/{_STUB_PRODUCT_ID}/price-calc",
            json={"input_cost": "100.00"},
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
    """Flag-disabled 404 response carries a valid JSON body.

    Ensures the error handler produces the standard FastAPI HTTPException
    envelope (not a plain string or HTML error page).
    """
    with patch("app.modules.pricing.router.settings") as mock_settings:
        mock_settings.FEATURE_PRICE_CALCULATOR_ENABLED = False

        response = await stub_pricing_client.post(
            f"/api/v1/products/{_STUB_PRODUCT_ID}/price-calc",
            json={"input_cost": "250.00", "target_margin_pct": "35"},
        )

    assert response.status_code == 404
    body = response.json()
    assert isinstance(body, dict)
    assert "detail" in body


# ── Test 2: POST route reachable when flag enabled ────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_price_calc_route_reachable_when_flag_enabled(stub_pricing_client):
    """FEATURE_PRICE_CALCULATOR_ENABLED=True → POST does NOT return the flag-guard 404.

    The default value of ``settings.FEATURE_PRICE_CALCULATOR_ENABLED`` is True
    (per config.py); no patching needed for the flag.

    The response may be:
    - 200 if DB is seeded + product + category exist (full happy path)
    - 404 from the ownership service (product not found — NOT from the flag guard)
    - 422 if Pydantic rejects the request body
    - 500 if DB connection is down (infra-gated — we accept this)

    ANY response other than the flag-guard 404 confirms the guard did NOT fire.
    This assertion is meaningful in CI without a live DB: the flag-guard 404
    is the ONLY path that sets detail == "Price Calculator is disabled in this
    environment" for a syntactically valid POST.

    If the service layer raises an exception due to missing DB infra, the test
    skips gracefully.
    """
    response = await stub_pricing_client.post(
        f"/api/v1/products/{_STUB_PRODUCT_ID}/price-calc",
        json={"input_cost": "100.00"},
    )

    # The flag-guard 404 must NOT appear when the flag is enabled.
    if response.status_code == 404:
        body = response.json()
        assert (
            body.get("detail") != "Price Calculator is disabled in this environment"
        ), (
            "Flag guard fired even though FEATURE_PRICE_CALCULATOR_ENABLED=True (default). "
            f"Full response: {body}"
        )
        # A real 404 from the service (product not found) is acceptable.
        return

    # If the service blows up due to missing DB infra, skip rather than fail.
    if response.status_code == 500:
        body_text = response.text
        if any(
            keyword in body_text
            for keyword in ("Connection refused", "could not connect", "asyncpg")
        ):
            pytest.skip(
                "DB infra not available — flag-enabled path is infra-gated; "
                "flag-guard 404 path (test 1) is the authoritative smoke test"
            )

    # Successful reach: 200, 400, 404, 422, 500 are acceptable (not the flag-guard 404).
    assert response.status_code in {200, 400, 404, 422, 500}, (
        f"Unexpected status {response.status_code}: {response.text}"
    )
