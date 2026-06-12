"""Integration smoke test — FEATURE_XLSX_EXPORT_ENABLED flag guard.

Session: mesell-xlsx-export-backend-session-1
Per FEATURE_PLAN.md D2 + Master Plan §3.2 backend feature-flag protocol.
R1 RULING IN EFFECT (master-confirmed): POST-only flag gate; GET /exports/{id}
stays UNGATED — in-flight export polls must keep working.

Two test paths covered
----------------------
1. **404-when-disabled** (``FEATURE_XLSX_EXPORT_ENABLED=False``):
   POST /products/{id}/export-xlsx returns
   ``{"detail": "XLSX export is disabled in this environment"}`` with
   HTTP 404 regardless of request content.
   This path is fully self-contained — no DB or Valkey required.

2. **Route-reachable when enabled** (``FEATURE_XLSX_EXPORT_ENABLED=True``,
   the default):
   POST /products/{id}/export-xlsx is reachable (does NOT return the flag-guard
   404) when the flag is on.  Full end-to-end response is infra-gated.
   When infra is unavailable the test confirms a non-flag-guard response
   (200 / 202 / 400 / 422 / 500 — anything except the specific 404 the
   flag guard emits) so the gate is meaningful even in CI without a live DB.

3. **GET /exports/{id} always reachable** (R1 ruling):
   GET /exports/{id} is NOT gated by FEATURE_XLSX_EXPORT_ENABLED.
   Even when the flag is False the poll endpoint does not return the
   flag-guard 404 — it returns 401 (auth checks before service) or
   whatever the service raises (404 export-not-found, etc.).
   This test verifies the guard code is absent from the GET handler by
   confirming the response is NOT the flag-guard 404 detail string.

Fixture strategy
----------------
- ``stub_export_client`` creates an in-process ASGI client with TWO dependency
  overrides:
    * ``get_current_user`` → a stub that returns a synthetic ``CurrentUser``
      so no valid JWT or DB user record is required.
    * ``get_db`` → NOT overridden for the flag-disabled path (the guard fires
      before any DB call, so DB is never touched for test paths 1 and 3).
- ``settings.FEATURE_XLSX_EXPORT_ENABLED`` is patched at the router import
  surface via ``unittest.mock.patch`` — specifically
  ``app.modules.export.router.settings`` (the module-level name in the router,
  NOT ``app.shared.config.settings``) per the image-precheck + smart-picker
  precedent. This makes the patch active only within the ``with patch(...)``
  block and is automatically restored when the block exits.
- The ``iam_client`` fixture (from ``integration/conftest.py``) is NOT used
  here — that fixture requires an active dev tunnel for DB + Valkey. The stub
  fixture is lighter and self-contained for the flag-guard purpose.

Phone-prefix convention: ``+9155500XXXXX`` for teardown-compatible user writes
(none in this test — stub auth bypasses DB user lookup entirely).
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

# ── Stub user injected into every request instead of a real JWT resolve ───────

_STUB_USER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000ee")
_STUB_PLAN: str = "free"

# A random product UUID used as the path param in all export POST requests.
_STUB_PRODUCT_ID = uuid.UUID("00000000-0000-0000-0000-000000000011")
# A random export UUID used as the path param in all GET export requests.
_STUB_EXPORT_ID = uuid.UUID("00000000-0000-0000-0000-000000000022")


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
async def stub_export_client():
    """ASGI client with stub auth override; NO DB/Valkey required.

    Only ``get_current_user`` is overridden — the DB override is left out
    intentionally so that tests needing DB access can hit the real dev-tunnel
    URL (infra-gated tests skip on connection failure at the service layer).
    The flag-guard tests fire BEFORE any DB call, so DB access is irrelevant
    for those assertions.
    """
    app.dependency_overrides[get_current_user] = _stub_get_current_user
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        async with app.router.lifespan_context(app):
            yield ac
    app.dependency_overrides.pop(get_current_user, None)


# ── Test 1: 404 on POST when flag disabled ────────────────────────────────────


@pytest.mark.asyncio
async def test_export_post_returns_404_when_flag_disabled(stub_export_client):
    """FEATURE_XLSX_EXPORT_ENABLED=False → POST returns 404 with locked detail.

    Patches ``app.modules.export.router.settings`` at the module level so
    the guard expression ``if not settings.FEATURE_XLSX_EXPORT_ENABLED``
    evaluates True.  Auth is stubbed so the dependency chain resolves without
    a real JWT.

    Acceptance criteria (FEATURE_PLAN.md D2 + Master Plan §3.2):
    - HTTP 404
    - body["detail"] == "XLSX export is disabled in this environment"
    """
    with patch("app.modules.export.router.settings") as mock_settings:
        mock_settings.FEATURE_XLSX_EXPORT_ENABLED = False

        response = await stub_export_client.post(
            f"/api/v1/products/{_STUB_PRODUCT_ID}/export-xlsx",
            json={"format": "xlsx_only"},
        )

    assert response.status_code == 404, (
        f"Expected 404 when flag is disabled, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body.get("detail") == "XLSX export is disabled in this environment", (
        f"Unexpected detail: {body.get('detail')!r}"
    )


@pytest.mark.asyncio
async def test_export_post_flag_off_404_body_is_json(stub_export_client):
    """Flag-disabled 404 response carries a valid JSON body.

    Ensures the error handler produces the standard FastAPI HTTPException
    envelope (not a plain string or HTML error page).
    """
    with patch("app.modules.export.router.settings") as mock_settings:
        mock_settings.FEATURE_XLSX_EXPORT_ENABLED = False

        response = await stub_export_client.post(
            f"/api/v1/products/{_STUB_PRODUCT_ID}/export-xlsx",
            json={"format": "xlsx_with_images"},
        )

    assert response.status_code == 404
    body = response.json()
    assert isinstance(body, dict)
    assert "detail" in body


# ── Test 2: POST route reachable when flag enabled ────────────────────────────


@pytest.mark.asyncio
async def test_export_post_route_reachable_when_flag_enabled(stub_export_client):
    """FEATURE_XLSX_EXPORT_ENABLED=True → POST does NOT return the flag-guard 404.

    The default value of ``settings.FEATURE_XLSX_EXPORT_ENABLED`` is True
    (per config.py); no patching needed for the flag.

    The response may be:
    - 202 if DB is seeded + Celery is mocked (full happy path)
    - 404 from the ownership service (product not found — NOT from the flag guard)
    - 422 if Pydantic rejects the request body
    - 500 if DB connection is down (infra-gated — we accept this)

    ANY response other than the flag-guard 404 confirms the guard did NOT fire.
    This assertion is meaningful in CI without a live DB: the flag-guard 404
    is the ONLY path that sets detail == "XLSX export is disabled in this
    environment" for a syntactically valid POST.

    If the service layer raises an exception that results in 500 due to
    missing DB infra, the test skips gracefully.
    """
    response = await stub_export_client.post(
        f"/api/v1/products/{_STUB_PRODUCT_ID}/export-xlsx",
        json={"format": "xlsx_only"},
    )

    # The flag-guard 404 must NOT appear when the flag is enabled.
    if response.status_code == 404:
        body = response.json()
        assert body.get("detail") != "XLSX export is disabled in this environment", (
            "Flag guard fired even though FEATURE_XLSX_EXPORT_ENABLED=True (default). "
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

    # Successful reach: 202, 400, 422 are all acceptable (not the flag-guard 404).
    assert response.status_code in {202, 400, 404, 422, 500}, (
        f"Unexpected status {response.status_code}: {response.text}"
    )


# ── Test 3: GET /exports/{id} is NOT gated (R1 ruling) ───────────────────────


@pytest.mark.asyncio
async def test_export_get_not_gated_when_flag_disabled(stub_export_client):
    """GET /exports/{id} must NOT return the flag-guard 404 even when flag=False.

    R1 RULING IN EFFECT: in-flight export polls (GET /exports/{id}) must keep
    working regardless of the FEATURE_XLSX_EXPORT_ENABLED flag.  The flag gate
    lives ONLY in the POST handler.

    When flag=False:
    - POST /products/{id}/export-xlsx → 404 "XLSX export is disabled in this
      environment"  (verified by test 1)
    - GET /exports/{id} → anything EXCEPT that exact flag-guard 404 detail
      (no flag guard in the GET handler; typical response is 404 with a
      different detail from the export-not-found service path, or 500 if DB
      is unavailable).

    Acceptance: ``body.get("detail") != "XLSX export is disabled in this
    environment"`` — the guard string must not appear on the GET endpoint.
    """
    with patch("app.modules.export.router.settings") as mock_settings:
        mock_settings.FEATURE_XLSX_EXPORT_ENABLED = False

        response = await stub_export_client.get(
            f"/api/v1/exports/{_STUB_EXPORT_ID}",
        )

    body = response.json()
    assert body.get("detail") != "XLSX export is disabled in this environment", (
        "Flag guard incorrectly fires on GET /exports/{id} — R1 ruling violated. "
        f"Full response: {body}"
    )
    # Any non-flag-guard response is acceptable for the GET endpoint.
    # Typical: 404 "export not found" or 500 (DB unavailable).
    # The key invariant is that the flag-guard string does NOT appear.
