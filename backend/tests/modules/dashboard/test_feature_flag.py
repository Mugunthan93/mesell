"""Unit tests — FEATURE_TRACKING_DASHBOARD_ENABLED flag guard.

Session: mesell-flag-parity-sweep-session-1
Per FEATURE_PLAN.md §2.2 D3 + Master Plan §3.2 backend feature-flag protocol.

R1 RULING IN EFFECT (master-confirmed): 404-on-read is intentional here.
The read IS the feature — GET /api/v1/products is the entire dashboard surface.
D3 kill-switch semantics: when the flag is off, the whole dashboard is off,
including the read endpoint.

Two test paths covered
----------------------
1. **404-when-disabled** (``FEATURE_TRACKING_DASHBOARD_ENABLED=False``):
   GET /api/v1/products returns
   ``{"detail": "Tracking Dashboard is disabled in this environment"}`` with
   HTTP 404 regardless of request content.
   This path is fully self-contained — no DB or Valkey required.

2. **Route-reachable when enabled** (``FEATURE_TRACKING_DASHBOARD_ENABLED=True``,
   the default):
   GET /api/v1/products is reachable (does NOT return the flag-guard 404) when
   the flag is on.  Full end-to-end response is infra-gated (dev-tunnel DB
   required).  When infra is unavailable the test confirms a non-flag-guard
   response (anything except the 404 the flag guard emits) so the gate is
   meaningful in CI without a live DB.

Fixture strategy
----------------
- ``stub_dashboard_client`` creates an in-process ASGI client with a single
  dependency override:
    * ``get_current_user`` → a stub that returns a synthetic ``CurrentUser``
      so no valid JWT or DB user record is required.
- For the 404 path, ``get_db`` override is irrelevant — the flag guard fires
  before the service call, so the DB is never touched.
- ``settings.FEATURE_TRACKING_DASHBOARD_ENABLED`` is patched at the router
  import surface via ``unittest.mock.patch`` — specifically
  ``app.modules.dashboard.router.settings`` — per the smart-picker + export
  + pricing precedent. This makes the patch active only within the
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

_STUB_USER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000dd")
_STUB_PLAN: str = "free"


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
async def stub_dashboard_client():
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


# ── Test 1: 404 on GET when flag disabled ─────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dashboard_returns_404_when_flag_disabled(stub_dashboard_client):
    """FEATURE_TRACKING_DASHBOARD_ENABLED=False → GET returns 404 with locked detail.

    Patches ``app.modules.dashboard.router.settings`` at the module level so
    the guard expression ``if not settings.FEATURE_TRACKING_DASHBOARD_ENABLED``
    evaluates True.  Auth is stubbed so the dependency chain resolves without
    a real JWT.

    R1 RULING: this is a GET/read route, but D3 explicitly mandates 404-on-read
    because the dashboard list IS the feature — not a side-effect of it.

    Acceptance criteria (FEATURE_PLAN.md §2.2 D3 + Master Plan §3.2):
    - HTTP 404
    - body["detail"] == "Tracking Dashboard is disabled in this environment"
    """
    with patch("app.modules.dashboard.router.settings") as mock_settings:
        mock_settings.FEATURE_TRACKING_DASHBOARD_ENABLED = False

        response = await stub_dashboard_client.get(
            "/api/v1/products",
            params={"page": 1, "limit": 20},
        )

    assert response.status_code == 404, (
        f"Expected 404 when flag is disabled, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body.get("detail") == "Tracking Dashboard is disabled in this environment", (
        f"Unexpected detail: {body.get('detail')!r}"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dashboard_flag_off_404_body_is_json(stub_dashboard_client):
    """Flag-disabled 404 response carries a valid JSON body.

    Ensures the error handler produces the standard FastAPI HTTPException
    envelope (not a plain string or HTML error page).
    """
    with patch("app.modules.dashboard.router.settings") as mock_settings:
        mock_settings.FEATURE_TRACKING_DASHBOARD_ENABLED = False

        response = await stub_dashboard_client.get("/api/v1/products")

    assert response.status_code == 404
    body = response.json()
    assert isinstance(body, dict)
    assert "detail" in body


# ── Test 2: GET route reachable when flag enabled ─────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dashboard_route_reachable_when_flag_enabled(stub_dashboard_client):
    """FEATURE_TRACKING_DASHBOARD_ENABLED=True → GET does NOT return the flag-guard 404.

    The default value of ``settings.FEATURE_TRACKING_DASHBOARD_ENABLED`` is True
    (per config.py); no patching needed for the flag.

    The response may be:
    - 200 with an empty or populated products list (if DB available)
    - 400 if pagination params are invalid (unlikely — defaults are valid)
    - 500 if DB connection is down (infra-gated — we accept this)

    ANY response other than the flag-guard 404 confirms the guard did NOT fire.
    This assertion is meaningful in CI without a live DB: the flag-guard 404
    is the ONLY path that sets detail == "Tracking Dashboard is disabled in this
    environment" for a syntactically valid GET.

    If the service layer raises an exception due to missing DB infra, the test
    skips gracefully.
    """
    response = await stub_dashboard_client.get(
        "/api/v1/products",
        params={"page": 1, "limit": 20},
    )

    # The flag-guard 404 must NOT appear when the flag is enabled.
    if response.status_code == 404:
        body = response.json()
        assert (
            body.get("detail") != "Tracking Dashboard is disabled in this environment"
        ), (
            "Flag guard fired even though FEATURE_TRACKING_DASHBOARD_ENABLED=True (default). "
            f"Full response: {body}"
        )
        # A real 404 from the route/service is acceptable.
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

    # Successful reach: 200, 400, 422, 500 are all acceptable (not the flag-guard 404).
    assert response.status_code in {200, 400, 404, 422, 500}, (
        f"Unexpected status {response.status_code}: {response.text}"
    )
