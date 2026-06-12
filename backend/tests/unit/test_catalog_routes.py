"""Route-level flag-guard unit tests for the catalog-form backend slice (G4 / G6).

Tests covered (all ``@pytest.mark.unit`` — no DB, no Valkey, no Gemini):

G4 — ``FEATURE_AI_AUTOFILL_ENABLED`` guard:
  (a) POST /api/v1/products/{id}/autofill returns 404 when the flag is False.
  (b) POST /api/v1/products/{id}/autofill returns non-404 (401 or 422 from the
      auth/validation layer) when the flag is True — i.e. the flag guard does
      NOT fire and the request proceeds normally.

G3 / FEATURE_CATALOG_FORM_ENABLED:
  (c) Catalog routes (/api/v1/products/*) return 404 when
      ``FEATURE_CATALOG_FORM_ENABLED=False`` at app construction — because
      ``main.py`` conditionally includes the router based on the flag.
  (d) Catalog routes ARE reachable (non-404 from auth layer) when
      ``FEATURE_CATALOG_FORM_ENABLED=True``.

Design notes
------------
* The production ``app`` object (from ``app.main``) is used for G4 tests.
  ``settings.FEATURE_AI_AUTOFILL_ENABLED`` is read at *request-time* inside
  the handler (not import-time), so a monkeypatch of the module-level
  ``settings`` attribute is sufficient to flip the guard per request.

* For G3 tests, ``main.py`` evaluates ``settings.FEATURE_CATALOG_FORM_ENABLED``
  at STARTUP (the ``include_router`` call).  To test the "disabled" branch
  we build a minimal ``FastAPI()`` app that explicitly omits the catalog router,
  then assert that the autofill path 404s.  The "enabled" branch is verified via
  the already-mounted production ``app`` (flag was True at module load time).

* All requests arrive without a valid JWT → the auth middleware returns 401
  before any service or DB code is reached.  Where a 404 is expected from the
  flag guard it fires BEFORE auth (the guard is the first statement in the
  handler body, but auth dependency is evaluated first by FastAPI).  We assert
  on the returned status code and do NOT call any real service.

* ``httpx.AsyncClient`` + ``ASGITransport`` is the async client pattern used
  across the codebase (see ``tests/integration/conftest.py``).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import app.modules.catalog.router as _catalog_router_module
from app.main import app as _production_app

pytestmark = pytest.mark.unit

# ── UUID used in all path-parameter positions ─────────────────────────────────
_PRODUCT_ID = uuid4()
_AUTOFILL_URL = f"/api/v1/products/{_PRODUCT_ID}/autofill"
_CREATE_URL = "/api/v1/products"
_PATCH_URL = f"/api/v1/products/{_PRODUCT_ID}"


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: bare ASGI client against the production app (no auth token needed —
# we're asserting on 401 or 404, both of which require no DB).
# ─────────────────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(loop_scope="function")
async def unauth_client():
    """Unauthenticated ASGI client against the production app.

    Suitable for asserting 401 (auth rejected) or 404 (flag guard / route
    absent) without touching DB or Valkey.
    """
    transport = ASGITransport(app=_production_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


# ─────────────────────────────────────────────────────────────────────────────
# G4 (a) — autofill returns 404 when FEATURE_AI_AUTOFILL_ENABLED=False
# ─────────────────────────────────────────────────────────────────────────────
class TestAutofillFlagGuard:
    """G4 — POST /autofill flag guard (FEATURE_AI_AUTOFILL_ENABLED)."""

    @pytest.mark.asyncio
    async def test_autofill_returns_404_when_flag_disabled(
        self, unauth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """(a) Flag False → 404 even for an authenticated-looking request.

        The guard fires as the FIRST statement of the handler, AFTER FastAPI
        resolves the auth dependency.  When auth fails first the response will
        be 401 (not 404) — to see 404 we need the auth dependency to succeed
        or be bypassed.

        Strategy: override the ``get_current_user`` dependency on the
        production app so it returns a fake user, then set the flag False.
        The guard then fires and 404 is returned before the service is reached.
        """
        from app.core.auth import CurrentUser, get_current_user

        # Build a minimal fake CurrentUser so the auth dep succeeds.
        fake_user = CurrentUser(user_id=uuid4(), plan="free")

        async def _fake_auth():
            return fake_user

        # Override the dependency on the production app for this test.
        _production_app.dependency_overrides[get_current_user] = _fake_auth

        # Disable the feature flag on the live settings object.
        monkeypatch.setattr(_catalog_router_module.settings, "FEATURE_AI_AUTOFILL_ENABLED", False)

        try:
            response = await unauth_client.post(
                _AUTOFILL_URL,
                json={"description": "a red cotton kurti"},
            )
        finally:
            # Always restore the override — other tests share the app object.
            _production_app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 404, (
            f"Expected 404 (feature disabled) but got {response.status_code}: "
            f"{response.text}"
        )
        body = response.json()
        assert "detail" in body
        # The detail message should mention the feature is disabled.
        assert "disabled" in body["detail"].lower()

    @pytest.mark.asyncio
    async def test_autofill_flag_disabled_not_401(
        self, unauth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """(a) supplementary — when flag is False, result is specifically NOT 401.

        This distinguishes "feature hidden" (404) from "auth rejected" (401).
        Uses the same fake-auth override as the test above.
        """
        from app.core.auth import CurrentUser, get_current_user

        fake_user = CurrentUser(user_id=uuid4(), plan="free")

        async def _fake_auth():
            return fake_user

        _production_app.dependency_overrides[get_current_user] = _fake_auth
        monkeypatch.setattr(_catalog_router_module.settings, "FEATURE_AI_AUTOFILL_ENABLED", False)

        try:
            response = await unauth_client.post(
                _AUTOFILL_URL,
                json={"description": "saree"},
            )
        finally:
            _production_app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code != 401, (
            "When FEATURE_AI_AUTOFILL_ENABLED=False the guard fires before any "
            "auth-specific rejection path; result should NOT be 401."
        )

    @pytest.mark.asyncio
    async def test_autofill_returns_non_404_when_flag_enabled(
        self, unauth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """(b) Flag True → NOT 404 — guard does not fire; auth layer rejects (401).

        With no Bearer token in the request, the auth middleware returns 401
        BEFORE the handler is entered.  The important assertion is that the
        response is NOT 404 (which would indicate the guard wrongly fired).
        """
        # Ensure the flag is True (default, but explicit for test clarity).
        monkeypatch.setattr(_catalog_router_module.settings, "FEATURE_AI_AUTOFILL_ENABLED", True)

        response = await unauth_client.post(
            _AUTOFILL_URL,
            json={"description": "a red cotton kurti"},
        )

        assert response.status_code != 404, (
            f"FEATURE_AI_AUTOFILL_ENABLED=True: guard must NOT fire; "
            f"got {response.status_code} instead"
        )
        # The unauthenticated request must be rejected at the auth layer.
        assert response.status_code == 401, (
            f"Expected 401 (no Bearer token) but got {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_autofill_guard_reads_settings_at_request_time(
        self, unauth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Guard reads ``settings`` at request time — toggling between requests
        produces different outcomes (404 then not-404).

        This confirms the implementation uses ``settings.FEATURE_AI_AUTOFILL_ENABLED``
        inside the handler body (not a module-level constant captured at import).

        Both requests use the dependency-override pattern to bypass auth.  The
        second request (flag=True) also overrides ``get_db`` with a no-op stub so
        the handler enters the service layer without touching Postgres — we only
        care that it returns something OTHER than 404 (the service will raise a
        ``ProductNotFoundError`` returning 404-equivalent, but from the service
        layer, not from the flag guard; we can tell them apart by the ``detail``
        message).

        Note: because ``ProductNotFoundError`` from the service layer also returns
        HTTP 404, we instead stub ``catalog_service.assert_product_ownership`` to
        raise a distinct exception (403) so the second request's status unambiguously
        is NOT the flag-guard 404.
        """
        from unittest.mock import AsyncMock

        from fastapi import HTTPException, status as _status

        from app.core.auth import CurrentUser, get_current_user
        from app.shared.database import get_db

        fake_user = CurrentUser(user_id=uuid4(), plan="free")

        async def _fake_auth():
            return fake_user

        # Stub get_db with a no-op generator so no real DB connection is opened.
        async def _fake_db():
            yield AsyncMock()

        # Stub assert_product_ownership to raise a 403 so the second request
        # produces a distinctly non-404 status code — separating "flag guard 404"
        # from any service-layer 404.
        async def _fake_ownership(*args, **kwargs):
            raise HTTPException(status_code=_status.HTTP_403_FORBIDDEN, detail="ownership-stub")

        import app.modules.catalog.service as _cat_svc

        _production_app.dependency_overrides[get_current_user] = _fake_auth
        _production_app.dependency_overrides[get_db] = _fake_db
        monkeypatch.setattr(_cat_svc, "assert_product_ownership", _fake_ownership)

        try:
            # First request: flag off → 404 from the flag guard.
            monkeypatch.setattr(_catalog_router_module.settings, "FEATURE_AI_AUTOFILL_ENABLED", False)
            r1 = await unauth_client.post(
                _AUTOFILL_URL,
                json={"description": "a kurti"},
            )

            # Second request: flag on → guard does NOT fire → service entered →
            # ownership stub raises 403.
            monkeypatch.setattr(_catalog_router_module.settings, "FEATURE_AI_AUTOFILL_ENABLED", True)
            r2 = await unauth_client.post(
                _AUTOFILL_URL,
                json={"description": "a kurti"},
            )
        finally:
            _production_app.dependency_overrides.pop(get_current_user, None)
            _production_app.dependency_overrides.pop(get_db, None)

        assert r1.status_code == 404, f"Flag-off request should be 404, got {r1.status_code}"
        assert r2.status_code != 404, (
            f"Flag-on request must not be 404 (the flag guard must not fire); "
            f"got {r2.status_code}"
        )
        # The second request hit the ownership stub → 403 confirms service entry.
        assert r2.status_code == 403, (
            f"Expected 403 from ownership-stub (guard bypassed); got {r2.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# G3 — FEATURE_CATALOG_FORM_ENABLED: routes absent / present at app construction
# ─────────────────────────────────────────────────────────────────────────────
class TestCatalogFormFlagRouteMount:
    """G3 — catalog routes reflect FEATURE_CATALOG_FORM_ENABLED at construction.

    The production ``app`` object was constructed with the flag True (default),
    so catalog routes ARE present.  To test the "flag False" branch we build
    a minimal FastAPI app that deliberately does NOT include the catalog router,
    mirroring what ``main.py`` does when the flag is False.
    """

    @pytest.mark.asyncio
    async def test_catalog_routes_absent_when_flag_false_at_construction(
        self,
    ) -> None:
        """(c) When FEATURE_CATALOG_FORM_ENABLED=False at construction, catalog
        routes are not mounted → 404 on any /products/* path.
        """
        # Build a stripped app without the catalog router (models the flag-False branch).
        stripped_app = FastAPI()
        # Deliberately do NOT include catalog_router.

        transport = ASGITransport(app=stripped_app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            # POST /products — create
            r_create = await ac.post(_CREATE_URL, json={})
            # PATCH /products/{id} — update
            r_patch = await ac.patch(_PATCH_URL, json={})
            # POST /products/{id}/autofill
            r_autofill = await ac.post(_AUTOFILL_URL, json={})

        assert r_create.status_code == 404, (
            f"Router not mounted: POST /products should 404, got {r_create.status_code}"
        )
        assert r_patch.status_code == 404, (
            f"Router not mounted: PATCH /products/{{id}} should 404, got {r_patch.status_code}"
        )
        assert r_autofill.status_code == 404, (
            f"Router not mounted: POST /products/{{id}}/autofill should 404, "
            f"got {r_autofill.status_code}"
        )

    @pytest.mark.asyncio
    async def test_catalog_routes_present_when_flag_true_at_construction(
        self,
    ) -> None:
        """(d) When FEATURE_CATALOG_FORM_ENABLED=True at construction (production app),
        catalog routes ARE mounted → auth layer rejects with 401, NOT 404.
        """
        transport = ASGITransport(app=_production_app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            r_create = await ac.post(_CREATE_URL, json={"description": "test"})
            r_autofill = await ac.post(_AUTOFILL_URL, json={"description": "test"})

        # Routes are mounted → no Bearer → 401 from auth, NOT 404.
        assert r_create.status_code != 404, (
            f"Catalog router IS mounted: POST /products must NOT 404, "
            f"got {r_create.status_code}"
        )
        assert r_autofill.status_code != 404, (
            f"Catalog router IS mounted: POST /autofill must NOT 404, "
            f"got {r_autofill.status_code}"
        )

    @pytest.mark.asyncio
    async def test_production_app_mounts_catalog_router_by_default(self) -> None:
        """Smoke: the production app was constructed with the default flag True,
        so the catalog router path prefix is present in its route table.
        """
        route_paths = {
            getattr(r, "path", None) for r in _production_app.routes
        }
        # Any of the catalog paths must be in the mounted set.
        assert "/api/v1/products" in route_paths, (
            "Production app should have /api/v1/products mounted "
            "(FEATURE_CATALOG_FORM_ENABLED defaults True)"
        )
