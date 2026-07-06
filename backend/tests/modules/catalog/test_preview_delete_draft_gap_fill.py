"""CAT-BE-43 / CAT-BE-44 / CAT-BE-45
Gap-fill for delete and draft endpoints.

- CAT-BE-43  DELETE 204 + soft-not-hard (deleted_at set, row still exists)
- CAT-BE-44  DELETE cross-tenant → 404 (not 403)
- CAT-BE-45  GET /draft → 204 when no draft exists

NOTE: CAT-BE-40/41/42 (GET /preview flag-off / flag-on / unauth+not-found) were
REMOVED 2026-07-06 — the §10.B.4 Live Product Preview route was retired with
Feature 6 (frontend removed in PR #278). See BACKEND_ARCHITECTURE.md §17
F6-retirement amendment.

Route-level tests use the ASGI stub-auth client pattern.
Service-level tests call service methods directly.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from app.core.auth import get_current_user
from app.main import app
from app.modules.catalog import service as catalog_service
from app.modules.catalog.exceptions import ProductNotFoundError
from app.modules.catalog.schemas import CreateProductRequest
from app.shared.database import get_db


pytestmark = pytest.mark.asyncio


@dataclass(frozen=True)
class _StubUser:
    user_id: object
    plan: str = "free"


# ── CAT-BE-43: DELETE 204 + soft-not-hard ────────────────────────────────────

@pytest.mark.integration
async def test_delete_204_and_soft_delete(db, user, beauty_category, beauty_profile):
    """CAT-BE-43: soft_delete sets deleted_at, row still exists in DB."""
    from sqlalchemy import text as _text

    product = await catalog_service.create_product(
        user.id,
        "free",
        CreateProductRequest(category_id=beauty_category.id, name="SoftDeleteMe"),
        db=db,
    )

    # Soft-delete at the service layer (equivalent to DELETE route).
    await catalog_service.soft_delete(user.id, product.id, db=db)

    # The row MUST still exist (soft, not hard delete).
    result = await db.execute(
        _text("SELECT deleted_at FROM products WHERE id = :pid"),
        {"pid": str(product.id)},
    )
    row = result.fetchone()

    assert row is not None, (
        f"Product row must still exist after soft_delete (not hard delete); product.id={product.id}"
    )
    # deleted_at must be populated (not NULL).
    deleted_at = row[0]
    assert deleted_at is not None, (
        f"deleted_at must be set after soft_delete; got NULL"
    )


@pytest.mark.integration
async def test_delete_route_204(db, user, beauty_category, beauty_profile, catalog_route_client):
    """CAT-BE-43 route-level: DELETE /products/{id} → 204 body-less response."""
    product = await catalog_service.create_product(
        user.id,
        "free",
        CreateProductRequest(category_id=beauty_category.id, name="DeleteRoute"),
        db=db,
    )

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: _StubUser(user_id=user.id)
    try:
        resp = await catalog_route_client.delete(f"/api/v1/products/{product.id}")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 204, (
        f"Expected 204 on DELETE, got {resp.status_code}: {resp.text}"
    )
    assert len(resp.content) == 0, (
        f"204 response must have no body; got {resp.content!r}"
    )


# ── CAT-BE-44: DELETE cross-tenant → 404 ─────────────────────────────────────

@pytest.mark.integration
async def test_delete_cross_tenant_returns_404(
    db, user, other_user, beauty_category, beauty_profile
):
    """CAT-BE-44: user B tries to delete user A's product → ProductNotFoundError (404)."""
    product = await catalog_service.create_product(
        user.id,
        "free",
        CreateProductRequest(category_id=beauty_category.id, name="CrossTenantDelete"),
        db=db,
    )

    with pytest.raises(ProductNotFoundError):
        await catalog_service.soft_delete(other_user.id, product.id, db=db)


# ── CAT-BE-45: draft → 204 when no draft exists ──────────────────────────────

@pytest.mark.integration
async def test_draft_204_when_no_draft(db, user, beauty_category, beauty_profile):
    """CAT-BE-45: GET /draft returns 204 when no autosave has been created."""
    product = await catalog_service.create_product(
        user.id,
        "free",
        CreateProductRequest(category_id=beauty_category.id, name="NoDraft"),
        db=db,
    )

    # No autosave PATCH was issued — draft must be None.
    draft = await catalog_service.get_draft(user.id, product.id, db=db)
    assert draft is None, (
        f"get_draft must return None when no draft exists; got {draft!r}"
    )


@pytest.mark.integration
async def test_draft_route_204_no_body(db, user, beauty_category, beauty_profile, catalog_route_client):
    """CAT-BE-45 route-level: GET /products/{id}/draft → 204, no body."""
    product = await catalog_service.create_product(
        user.id,
        "free",
        CreateProductRequest(category_id=beauty_category.id, name="NoDraftRoute"),
        db=db,
    )

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: _StubUser(user_id=user.id)
    try:
        resp = await catalog_route_client.get(f"/api/v1/products/{product.id}/draft")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 204, (
        f"Expected 204 when no draft exists, got {resp.status_code}: {resp.text}"
    )
    assert len(resp.content) == 0, (
        f"204 must have no body; got {resp.content!r}"
    )
