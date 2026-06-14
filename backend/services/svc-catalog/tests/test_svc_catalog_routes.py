"""Route-level tests for svc-catalog — public router + internal shims.

Test strategy
-------------
These are UNIT-level route tests using httpx AsyncClient with the FastAPI
test app.  All service calls are mocked (``unittest.mock.AsyncMock``); the DB
and Valkey are not reached.  We test:

* Correct HTTP method / path wiring.
* Auth enforcement: 401 when no Bearer token on public routes.
* Feature flag guards: 404 when FEATURE_AI_AUTOFILL_ENABLED=False and
  FEATURE_LIVE_PREVIEW_ENABLED=False (the latter is the default).
* Internal shim 401 when no JWT forwarded.
* Internal ownership-check: 200 + {owned, category_id} on success; 404 on
  ProductNotFoundError.
* Internal export-snapshot: 200 + frozen ExportSnapshotResponse shape.
* Internal list_products: 200 + PaginatedProductsInternalResponse shape.
* Internal validation-summary: 200 + ValidationSummaryInternalResponse shape.
* PatchProductRequest validation: 422 on empty body (no fields, no status).

Test class / fixture strategy
------------------------------
``_catalog_app`` builds the FastAPI app with the public + internal router mounted
and ALL middleware stripped (dependency_overrides handle auth).  A ``fake_user``
CurrentUser is registered via ``dependency_overrides`` for routes that need it.

For internal routes (no get_current_user dep), we set ``request.state.user``
by patching ``AuthContextMiddleware`` to always inject the fake_user.  The
simpler approach used here: pass ``Authorization: Bearer fake`` and patch the
``_decode_access_token`` path — but AuthContextMiddleware uses a try/except
that swallows decode errors (fail-open).  Instead we monkeypatch
``app.core.middleware.auth_mw.AuthContextMiddleware.dispatch`` directly.

Simpler pattern (used): override ``request.state`` via a minimal middleware
shim added after the router is built so internal routes see a live
``request.state.user``.

Notes
------
* ``asyncio_mode = auto`` in pytest.ini — no ``@pytest.mark.asyncio`` needed.
* Uses ``unittest.mock.patch`` / ``AsyncMock`` — no live DB or Valkey.
* Ruff-clean: F401 suppressed where needed via ``# noqa``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from starlette.middleware.base import BaseHTTPMiddleware

# ── ensure env before any app.* import ──────────────────────────────────────
# conftest.py sets the env at module level; this file is collected after conftest.
from app.core.auth import CurrentUser, get_current_user  # noqa: E402
from app.core.errors import register_error_handlers  # noqa: E402
from app.domain import (  # noqa: E402
    ExportSnapshotInternal,
    PaginatedProductsInternal,
    Product,
    ValidationSummaryInternal,
)
from app.exceptions import ProductNotFoundError  # noqa: E402
from app.internal_router import router as internal_router  # noqa: E402
from app.router import router as public_router  # noqa: E402
from app.shared.database import get_db  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────
# Shared test fixtures
# ─────────────────────────────────────────────────────────────────────────────

FAKE_USER_ID = uuid4()
FAKE_CATEGORY_ID = uuid4()
FAKE_PRODUCT_ID = uuid4()
FAKE_CATALOG_ID = uuid4()

FAKE_USER = CurrentUser(user_id=FAKE_USER_ID, plan="free")


@dataclass(frozen=True)
class _FakeProduct:
    """Minimal domain Product stand-in (avoids importing ORM models)."""

    id: UUID = FAKE_PRODUCT_ID
    user_id: UUID = FAKE_USER_ID
    catalog_id: UUID = FAKE_CATALOG_ID
    category_id: UUID = FAKE_CATEGORY_ID
    name: str | None = "Test Product"
    status: Literal["draft", "ready"] = "draft"
    fields: dict = None
    ai_suggestions: dict = None
    created_at: str = "2026-06-14T10:00:00+00:00"
    updated_at: str = "2026-06-14T10:00:00+00:00"
    deleted_at: None = None

    def __post_init__(self):
        object.__setattr__(self, "fields", self.fields or {})
        object.__setattr__(self, "ai_suggestions", self.ai_suggestions or {})


class _FakeDB:
    """No-op async context manager for DB session dependency override."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass


async def _fake_db_gen():
    yield _FakeDB()


class _InjectUserMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that injects FAKE_USER into request.state.user.

    Used to simulate AuthContextMiddleware's JWT-decode result for internal
    routes (which don't use get_current_user dep injection).
    """

    async def dispatch(self, request: Request, call_next):
        request.state.user = FAKE_USER
        return await call_next(request)


def _make_test_app(*, inject_user_mw: bool = True) -> FastAPI:
    """Build a minimal FastAPI test application with the catalog routers.

    ``inject_user_mw=True`` adds the _InjectUserMiddleware (needed for
    internal route tests where AuthContextMiddleware would normally run).
    For public route 401 tests set inject_user_mw=False and do NOT override
    get_current_user so the real TokenMissingError fires.
    """
    from app.shared.config import settings  # local to avoid early import

    # Temporarily enable the flag for mounting (tests patch it per-test).
    _orig = settings.FEATURE_CATALOG_FORM_ENABLED
    settings.FEATURE_CATALOG_FORM_ENABLED = True  # type: ignore[assignment]
    try:
        app = FastAPI()
        register_error_handlers(app)
        app.include_router(public_router)
        app.include_router(internal_router)
        if inject_user_mw:
            app.add_middleware(_InjectUserMiddleware)
    finally:
        settings.FEATURE_CATALOG_FORM_ENABLED = _orig  # type: ignore[assignment]
    return app


@pytest.fixture()
def catalog_app():
    """Test app with user middleware (for internal routes and auth-bypassed public)."""
    app = _make_test_app(inject_user_mw=True)
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_db] = _fake_db_gen
    return app


@pytest.fixture()
def unauth_app():
    """Test app WITHOUT user override — used for 401 tests on public routes."""
    app = _make_test_app(inject_user_mw=False)
    app.dependency_overrides[get_db] = _fake_db_gen
    # Do NOT override get_current_user — let TokenMissingError propagate.
    return app


# ─────────────────────────────────────────────────────────────────────────────
# Public route: POST /api/v1/products
# ─────────────────────────────────────────────────────────────────────────────


async def test_create_product_401(unauth_app):
    """Public routes require auth — 401 without Bearer token."""
    async with AsyncClient(
        transport=ASGITransport(app=unauth_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/products",
            json={"category_id": str(FAKE_CATEGORY_ID)},
        )
    assert resp.status_code == 401


async def test_create_product_happy(catalog_app):
    """POST /api/v1/products — 201 with ProductResponse shape."""
    fake_product = _FakeProduct()
    with patch("app.router.catalog_service.create_product", new=AsyncMock(return_value=fake_product)):
        async with AsyncClient(
            transport=ASGITransport(app=catalog_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/products",
                json={"category_id": str(FAKE_CATEGORY_ID)},
                headers={"Authorization": "Bearer fake"},
            )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == str(fake_product.id)
    assert body["category_id"] == str(FAKE_CATEGORY_ID)
    assert body["status"] == "draft"


async def test_create_product_422_bad_body(catalog_app):
    """POST /api/v1/products — 422 when category_id is missing."""
    async with AsyncClient(
        transport=ASGITransport(app=catalog_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/products",
            json={},
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Public route: PATCH /api/v1/products/{id}
# ─────────────────────────────────────────────────────────────────────────────


async def test_patch_product_401(unauth_app):
    """PATCH /api/v1/products/{id} — 401 without token."""
    async with AsyncClient(
        transport=ASGITransport(app=unauth_app), base_url="http://test"
    ) as client:
        resp = await client.patch(
            f"/api/v1/products/{FAKE_PRODUCT_ID}",
            json={"fields": {"color": "red"}},
        )
    assert resp.status_code == 401


async def test_patch_product_422_empty_body(catalog_app):
    """PATCH /api/v1/products/{id} — 422 on empty body (§10.B.2 validator)."""
    async with AsyncClient(
        transport=ASGITransport(app=catalog_app), base_url="http://test"
    ) as client:
        resp = await client.patch(
            f"/api/v1/products/{FAKE_PRODUCT_ID}",
            json={},
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 422


async def test_patch_product_happy(catalog_app):
    """PATCH /api/v1/products/{id} — 200 with ProductResponse shape."""
    fake_product = _FakeProduct()
    with patch("app.router.catalog_service.patch_product", new=AsyncMock(return_value=fake_product)):
        async with AsyncClient(
            transport=ASGITransport(app=catalog_app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/api/v1/products/{FAKE_PRODUCT_ID}",
                json={"fields": {"color": "red"}},
                headers={"Authorization": "Bearer fake"},
            )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(FAKE_PRODUCT_ID)


async def test_patch_product_autosave_header(catalog_app):
    """PATCH with X-Autosave: true — is_autosave forwarded to service."""
    fake_product = _FakeProduct()
    mock_patch = AsyncMock(return_value=fake_product)
    with patch("app.router.catalog_service.patch_product", new=mock_patch):
        async with AsyncClient(
            transport=ASGITransport(app=catalog_app), base_url="http://test"
        ) as client:
            await client.patch(
                f"/api/v1/products/{FAKE_PRODUCT_ID}",
                json={"fields": {"color": "blue"}},
                headers={"Authorization": "Bearer fake", "x-autosave": "true"},
            )
    _, call_kwargs = mock_patch.call_args
    assert call_kwargs.get("is_autosave") is True


# ─────────────────────────────────────────────────────────────────────────────
# Public route: POST /api/v1/products/{id}/autofill
# ─────────────────────────────────────────────────────────────────────────────


async def test_autofill_404_when_flag_off(catalog_app):
    """POST /api/v1/products/{id}/autofill — 404 when FEATURE_AI_AUTOFILL_ENABLED=False."""
    from app.shared import config as _cfg_module

    _orig = _cfg_module.settings.FEATURE_AI_AUTOFILL_ENABLED
    _cfg_module.settings.FEATURE_AI_AUTOFILL_ENABLED = False  # type: ignore
    try:
        async with AsyncClient(
            transport=ASGITransport(app=catalog_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/products/{FAKE_PRODUCT_ID}/autofill",
                json={"description": "A short description of the product"},
                headers={"Authorization": "Bearer fake"},
            )
        assert resp.status_code == 404
        assert "disabled" in resp.json().get("detail", "").lower()
    finally:
        _cfg_module.settings.FEATURE_AI_AUTOFILL_ENABLED = _orig  # type: ignore


async def test_autofill_401(unauth_app):
    """POST /api/v1/products/{id}/autofill — 401 without token."""
    async with AsyncClient(
        transport=ASGITransport(app=unauth_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/v1/products/{FAKE_PRODUCT_ID}/autofill",
            json={"description": "test"},
        )
    assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# Public route: GET /api/v1/products/{id}/preview
# ─────────────────────────────────────────────────────────────────────────────


async def test_preview_404_default_flag_off(catalog_app):
    """GET /api/v1/products/{id}/preview — 404 by default (FEATURE_LIVE_PREVIEW_ENABLED=False)."""
    # FEATURE_LIVE_PREVIEW_ENABLED defaults to False — the ONLY V1 default-False flag.
    # We do NOT patch the flag; the default IS False.
    from app.shared import config as _cfg_module

    assert _cfg_module.settings.FEATURE_LIVE_PREVIEW_ENABLED is False, (
        "FEATURE_LIVE_PREVIEW_ENABLED must default to False per MS-H spec"
    )
    async with AsyncClient(
        transport=ASGITransport(app=catalog_app), base_url="http://test"
    ) as client:
        resp = await client.get(
            f"/api/v1/products/{FAKE_PRODUCT_ID}/preview",
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 404
    body = resp.json()
    assert body.get("code") == "feature.live_preview.disabled"


async def test_preview_401(unauth_app):
    """GET /api/v1/products/{id}/preview — 401 without token."""
    async with AsyncClient(
        transport=ASGITransport(app=unauth_app), base_url="http://test"
    ) as client:
        resp = await client.get(f"/api/v1/products/{FAKE_PRODUCT_ID}/preview")
    assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# Public route: DELETE /api/v1/products/{id}
# ─────────────────────────────────────────────────────────────────────────────


async def test_delete_product_401(unauth_app):
    """DELETE /api/v1/products/{id} — 401 without token."""
    async with AsyncClient(
        transport=ASGITransport(app=unauth_app), base_url="http://test"
    ) as client:
        resp = await client.delete(f"/api/v1/products/{FAKE_PRODUCT_ID}")
    assert resp.status_code == 401


async def test_delete_product_204(catalog_app):
    """DELETE /api/v1/products/{id} — 204 on success."""
    with patch("app.router.catalog_service.soft_delete", new=AsyncMock(return_value=None)):
        async with AsyncClient(
            transport=ASGITransport(app=catalog_app), base_url="http://test"
        ) as client:
            resp = await client.delete(
                f"/api/v1/products/{FAKE_PRODUCT_ID}",
                headers={"Authorization": "Bearer fake"},
            )
    assert resp.status_code == 204
    assert resp.content == b""


# ─────────────────────────────────────────────────────────────────────────────
# Public route: GET /api/v1/products/{id}/draft
# ─────────────────────────────────────────────────────────────────────────────


async def test_get_draft_401(unauth_app):
    """GET /api/v1/products/{id}/draft — 401 without token."""
    async with AsyncClient(
        transport=ASGITransport(app=unauth_app), base_url="http://test"
    ) as client:
        resp = await client.get(f"/api/v1/products/{FAKE_PRODUCT_ID}/draft")
    assert resp.status_code == 401


async def test_get_draft_204_when_none(catalog_app):
    """GET /api/v1/products/{id}/draft — 204 when service returns None."""
    with patch("app.router.catalog_service.get_draft", new=AsyncMock(return_value=None)):
        async with AsyncClient(
            transport=ASGITransport(app=catalog_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/products/{FAKE_PRODUCT_ID}/draft",
                headers={"Authorization": "Bearer fake"},
            )
    assert resp.status_code == 204
    assert resp.content == b""


async def test_get_draft_200_with_snapshot(catalog_app):
    """GET /api/v1/products/{id}/draft — 200 with ProductDraftResponse when draft exists."""
    from datetime import datetime, timezone

    @dataclass(frozen=True)
    class _FakeDraft:
        user_id: UUID = FAKE_USER_ID
        product_id: UUID = FAKE_PRODUCT_ID
        fields: dict = None
        last_updated: datetime = None
        autosave_count: int = 3

        def __post_init__(self):
            object.__setattr__(self, "fields", self.fields or {"color": "red"})
            object.__setattr__(
                self, "last_updated", self.last_updated or datetime.now(timezone.utc)
            )

    fake_draft = _FakeDraft()
    with patch("app.router.catalog_service.get_draft", new=AsyncMock(return_value=fake_draft)):
        async with AsyncClient(
            transport=ASGITransport(app=catalog_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/products/{FAKE_PRODUCT_ID}/draft",
                headers={"Authorization": "Bearer fake"},
            )
    assert resp.status_code == 200
    body = resp.json()
    assert body["autosave_count"] == 3
    assert "last_updated" in body
    assert body["fields"]["color"] == "red"


# ─────────────────────────────────────────────────────────────────────────────
# Internal shim: GET /internal/products/{id}/ownership-check
# ─────────────────────────────────────────────────────────────────────────────


async def test_ownership_check_401_no_user(unauth_app):
    """GET /internal/products/{id}/ownership-check — 401 when no JWT in state."""
    # unauth_app has no _InjectUserMiddleware → request.state.user = None
    async with AsyncClient(
        transport=ASGITransport(app=unauth_app), base_url="http://test"
    ) as client:
        resp = await client.get(
            f"/internal/products/{FAKE_PRODUCT_ID}/ownership-check",
            params={"user_id": str(FAKE_USER_ID)},
        )
    assert resp.status_code == 401


async def test_ownership_check_200_widened(catalog_app):
    """GET /internal/products/{id}/ownership-check — 200 with {owned, category_id}."""
    fake_snapshot = ExportSnapshotInternal(
        product_id=FAKE_PRODUCT_ID,
        category_id=FAKE_CATEGORY_ID,
        fields={"color": "red"},
        ai_suggestions={},
        image_refs=(),
        validation_summary=ValidationSummaryInternal(
            product_id=FAKE_PRODUCT_ID,
            compulsory_filled=2,
            compulsory_total=3,
            optional_filled=0,
            optional_total=1,
            has_validation_errors=False,
            status="draft",
        ),
    )
    with (
        patch(
            "app.internal_router.catalog_service.assert_product_ownership",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.internal_router.catalog_service.get_product_for_export",
            new=AsyncMock(return_value=fake_snapshot),
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=catalog_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/internal/products/{FAKE_PRODUCT_ID}/ownership-check",
                params={"user_id": str(FAKE_USER_ID)},
            )
    assert resp.status_code == 200
    body = resp.json()
    assert body["owned"] is True
    assert body["category_id"] == str(FAKE_CATEGORY_ID), (
        "category_id MUST be present in 200 body — pricing consumer reads it (§0.6)"
    )


async def test_ownership_check_404_not_owned(catalog_app):
    """GET /internal/products/{id}/ownership-check — 404 on ProductNotFoundError."""
    with patch(
        "app.internal_router.catalog_service.assert_product_ownership",
        new=AsyncMock(side_effect=ProductNotFoundError()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=catalog_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/internal/products/{FAKE_PRODUCT_ID}/ownership-check",
                params={"user_id": str(FAKE_USER_ID)},
            )
    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Internal shim: GET /internal/products/{id}/export-snapshot
# ─────────────────────────────────────────────────────────────────────────────


async def test_export_snapshot_401_no_user(unauth_app):
    """GET /internal/products/{id}/export-snapshot — 401 when no JWT in state."""
    async with AsyncClient(
        transport=ASGITransport(app=unauth_app), base_url="http://test"
    ) as client:
        resp = await client.get(
            f"/internal/products/{FAKE_PRODUCT_ID}/export-snapshot",
            params={"user_id": str(FAKE_USER_ID)},
        )
    assert resp.status_code == 401


async def test_export_snapshot_200_shape(catalog_app):
    """GET /internal/products/{id}/export-snapshot — 200 with ExportSnapshotResponse shape."""
    fake_snapshot = ExportSnapshotInternal(
        product_id=FAKE_PRODUCT_ID,
        category_id=FAKE_CATEGORY_ID,
        fields={"color": "red", "size": "M"},
        ai_suggestions={"color": {"value": "red", "confidence": 0.9, "source": "ai"}},
        image_refs=(),
        validation_summary=ValidationSummaryInternal(
            product_id=FAKE_PRODUCT_ID,
            compulsory_filled=2,
            compulsory_total=3,
            optional_filled=0,
            optional_total=1,
            has_validation_errors=False,
            status="draft",
        ),
    )
    with patch(
        "app.internal_router.catalog_service.get_product_for_export",
        new=AsyncMock(return_value=fake_snapshot),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=catalog_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/internal/products/{FAKE_PRODUCT_ID}/export-snapshot",
                params={"user_id": str(FAKE_USER_ID)},
            )
    assert resp.status_code == 200
    body = resp.json()
    # Verify all 6 frozen fields per MS-A contract + export catalog_client
    assert body["product_id"] == str(FAKE_PRODUCT_ID)
    assert body["category_id"] == str(FAKE_CATEGORY_ID)
    assert body["fields"]["color"] == "red"
    assert isinstance(body["ai_suggestions"], dict)
    assert isinstance(body["image_refs"], list)
    vs = body["validation_summary"]
    assert vs["status"] == "draft"
    assert "compulsory_filled" in vs


async def test_export_snapshot_404(catalog_app):
    """GET /internal/products/{id}/export-snapshot — 404 on ProductNotFoundError."""
    with patch(
        "app.internal_router.catalog_service.get_product_for_export",
        new=AsyncMock(side_effect=ProductNotFoundError()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=catalog_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/internal/products/{FAKE_PRODUCT_ID}/export-snapshot",
                params={"user_id": str(FAKE_USER_ID)},
            )
    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Internal shim: GET /internal/products (list_products)
# ─────────────────────────────────────────────────────────────────────────────


async def test_list_products_internal_401(unauth_app):
    """GET /internal/products — 401 when no JWT in state."""
    async with AsyncClient(
        transport=ASGITransport(app=unauth_app), base_url="http://test"
    ) as client:
        resp = await client.get("/internal/products")
    assert resp.status_code == 401


async def test_list_products_internal_200(catalog_app):
    """GET /internal/products — 200 with PaginatedProductsInternalResponse shape."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    fake_product = Product(
        id=FAKE_PRODUCT_ID,
        user_id=FAKE_USER_ID,
        catalog_id=FAKE_CATALOG_ID,
        category_id=FAKE_CATEGORY_ID,
        name="Test",
        status="draft",
        fields={"color": "red"},
        ai_suggestions={},
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    fake_paginated = PaginatedProductsInternal(
        items=(fake_product,),
        total=1,
        page=1,
        limit=20,
    )
    with patch(
        "app.internal_router.catalog_service.list_products",
        new=AsyncMock(return_value=fake_paginated),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=catalog_app), base_url="http://test"
        ) as client:
            resp = await client.get("/internal/products", params={"page": 1, "limit": 20})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    # Verify dashboard catalog_client hydration fields present
    assert item["id"] == str(FAKE_PRODUCT_ID)
    assert item["user_id"] == str(FAKE_USER_ID)
    assert item["catalog_id"] == str(FAKE_CATALOG_ID)
    assert item["category_id"] == str(FAKE_CATEGORY_ID)
    assert item["status"] == "draft"


async def test_list_products_internal_empty(catalog_app):
    """GET /internal/products — 200 with empty items (first-time-seller state)."""
    fake_paginated = PaginatedProductsInternal(items=(), total=0, page=1, limit=20)
    with patch(
        "app.internal_router.catalog_service.list_products",
        new=AsyncMock(return_value=fake_paginated),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=catalog_app), base_url="http://test"
        ) as client:
            resp = await client.get("/internal/products")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


# ─────────────────────────────────────────────────────────────────────────────
# Internal shim: GET /internal/products/{id}/validation-summary (defensive)
# ─────────────────────────────────────────────────────────────────────────────


async def test_validation_summary_internal_401(unauth_app):
    """GET /internal/products/{id}/validation-summary — 401 when no JWT."""
    async with AsyncClient(
        transport=ASGITransport(app=unauth_app), base_url="http://test"
    ) as client:
        resp = await client.get(
            f"/internal/products/{FAKE_PRODUCT_ID}/validation-summary",
            params={"user_id": str(FAKE_USER_ID)},
        )
    assert resp.status_code == 401


async def test_validation_summary_internal_200(catalog_app):
    """GET /internal/products/{id}/validation-summary — 200 with summary shape."""
    fake_summary = ValidationSummaryInternal(
        product_id=FAKE_PRODUCT_ID,
        compulsory_filled=2,
        compulsory_total=3,
        optional_filled=1,
        optional_total=2,
        has_validation_errors=False,
        status="draft",
    )
    with patch(
        "app.internal_router.catalog_service.get_validation_summary",
        new=AsyncMock(return_value=fake_summary),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=catalog_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/internal/products/{FAKE_PRODUCT_ID}/validation-summary",
                params={"user_id": str(FAKE_USER_ID)},
            )
    assert resp.status_code == 200
    body = resp.json()
    assert body["product_id"] == str(FAKE_PRODUCT_ID)
    assert body["compulsory_filled"] == 2
    assert body["status"] == "draft"
    assert body["has_validation_errors"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Route mounting verification
# ─────────────────────────────────────────────────────────────────────────────


def test_public_routes_count(catalog_app):
    """6 public APIRoute objects are mounted from the public router."""
    from fastapi.routing import APIRoute

    api_routes = [r for r in catalog_app.routes if isinstance(r, APIRoute)]
    # 6 public routes (POST /products, PATCH /products/{id},
    # POST /products/{id}/autofill, GET /products/{id}/preview,
    # DELETE /products/{id}, GET /products/{id}/draft)
    # + 4 internal routes = 10 total APIRoute objects
    public = [r for r in api_routes if r.path.startswith("/api/v1/")]
    assert len(public) == 6, (
        f"Expected 6 public APIRoute objects; got {len(public)}: "
        f"{[r.path for r in public]}"
    )


def test_internal_routes_count(catalog_app):
    """4 internal APIRoute objects are mounted (3 live + 1 defensive)."""
    from fastapi.routing import APIRoute

    api_routes = [r for r in catalog_app.routes if isinstance(r, APIRoute)]
    internal = [r for r in api_routes if r.path.startswith("/internal/")]
    assert len(internal) == 4, (
        f"Expected 4 internal APIRoute objects; got {len(internal)}: "
        f"{[r.path for r in internal]}"
    )


def test_internal_routes_not_in_schema(catalog_app):
    """All /internal/* routes have include_in_schema=False."""
    from fastapi.routing import APIRoute

    for route in catalog_app.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/internal/"):
            assert route.include_in_schema is False, (
                f"/internal route {route.path} must have include_in_schema=False"
            )
