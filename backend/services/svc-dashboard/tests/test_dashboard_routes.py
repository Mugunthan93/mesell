"""Route-level tests for svc-dashboard via FastAPI TestClient (spec §3.B acceptance).

The svc-dashboard has NO live infrastructure dependencies in this suite:

* ``get_current_user`` is overridden via ``dependency_overrides`` — no real JWT
  or DB user row is required.
* ``catalog_client.list_products`` and ``customer_client.get_onboarding_completeness``
  are patched at the ``app.service`` import surface using ``monkeypatch.setattr``
  — no real HTTP calls to the monolith ClusterIP.

Coverage ported from the monolith behavioural suite
-----------------------------------------------------
1. **Happy path** — authenticated GET, flag enabled, mocked shims return 1 product
   + 5-field completeness → 200 with composed ``DashboardResponse`` (product_id rename,
   total/page/limit passthrough, onboarding_completeness header).
2. **Empty state** — mocked catalog returns zero items → 200 with ``products: []``,
   ``total: 0`` — NOT 404 (first-time seller state, §13.B lock).
3. **Feature-flag 404** — ``FEATURE_TRACKING_DASHBOARD_ENABLED=false`` → 404
   and NO shim call made (D3 kill-switch, §13.B + §13.I).
4. **Pagination validation** — ``page=0``, ``limit=0``, ``limit=101`` → 422 BEFORE
   any shim call (Pydantic ``Query`` Field constraint enforcement).
5. **Auth** — unauthenticated request → 401/403 (``TokenMissingError`` — no Bearer
   token supplied).

Non-tautological contract (pricing-lesson):
  Every assertion inspects a real response field (status_code, body field, absence
  of shim calls). ``assert True``-class echoes are a reject-class offence.

Isolation notes:
* The svc-dashboard app boots a FULL 6-middleware chain (CORSMiddleware + 5 others),
  including ``RateLimitMiddleware`` and ``AuthContextMiddleware``. The
  ``ASGITransport(raise_app_exceptions=False)`` mode surfaces HTTP exceptions
  as response objects (not as Python exceptions in the test body).
* ``get_db`` is overridden with a no-op async generator so the auth existence
  check never hits a real PostgreSQL instance.
* The ``_reset_shim_context`` fixture (conftest autouse) cleans the JWT/request-id
  context-vars between tests, which prevents leakage into shim assertions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.auth import CurrentUser, get_current_user
from app.core.extracted_clients import catalog_client, customer_client
from app.core.extracted_clients.catalog_client import (
    PaginatedProductsInternal,
    Product,
)
from app.core.extracted_clients.customer_client import ProfileCompleteness
from app.main import app
from app.schemas import DashboardResponse
from app.shared.database import get_db


# ─────────────────────────────────────────────────────────────────────────────
# Constants — synthetic test principals
# ─────────────────────────────────────────────────────────────────────────────
_STUB_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000dddddd")
_STUB_PLAN: str = "free"


# ─────────────────────────────────────────────────────────────────────────────
# Stub CurrentUser — satisfies the Depends(get_current_user) contract without
# a real JWT or DB user row.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class _StubCurrentUser:
    user_id: uuid.UUID = _STUB_USER_ID
    plan: str = _STUB_PLAN


async def _stub_get_current_user() -> CurrentUser:
    return _StubCurrentUser()  # type: ignore[return-value]


# ─────────────────────────────────────────────────────────────────────────────
# No-op get_db override — the shim tests do not touch PostgreSQL.
# ─────────────────────────────────────────────────────────────────────────────
async def _noop_get_db():
    """Yield a sentinel object; the route forwards it to the service which
    ignores it (shims accept ``db`` and discard it — HTTP-shim call-site parity)."""
    yield object()


# ─────────────────────────────────────────────────────────────────────────────
# Sample domain objects — used in happy path + empty state tests
# ─────────────────────────────────────────────────────────────────────────────
_NOW = datetime(2026, 6, 13, 10, 0, 0, tzinfo=timezone.utc)
_PRODUCT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CATEGORY_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

_SAMPLE_PRODUCT = Product(
    id=_PRODUCT_ID,
    user_id=_STUB_USER_ID,
    catalog_id=uuid.uuid4(),
    category_id=_CATEGORY_ID,
    name="Cotton Kurta",
    status="ready",
    fields={"color": "red"},
    ai_suggestions={},
    created_at=_NOW,
    updated_at=_NOW,
    deleted_at=None,
)

_SAMPLE_COMPLETENESS = ProfileCompleteness(
    base_complete_count=8,
    base_total_count=10,
    extension_complete_count=2,
    extension_total_count=5,
    onboarding_complete=False,
)

_PAGINATED_ONE = PaginatedProductsInternal(
    items=(_SAMPLE_PRODUCT,),
    total=1,
    page=1,
    limit=20,
)

_PAGINATED_ZERO = PaginatedProductsInternal(
    items=(),
    total=0,
    page=1,
    limit=20,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture — ASGI client with stub auth + no-op DB + NO shim patches
# (flag-gate + pagination tests fire before any shim call)
# ─────────────────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(loop_scope="function")
async def stub_client():
    """Client with auth + DB overridden; shims are NOT patched here.

    Used for tests where the flag guard or Pydantic validator fires BEFORE the
    service call — so no shim mock is needed.
    """
    app.dependency_overrides[get_current_user] = _stub_get_current_user
    app.dependency_overrides[get_db] = _noop_get_db

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        async with app.router.lifespan_context(app):
            yield ac

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture — ASGI client for unauthenticated requests (no overrides)
# ─────────────────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(loop_scope="function")
async def unauth_client():
    """Raw ASGI client — no auth override, no DB override.

    Used to verify that unauthenticated requests return 401/403 before any
    service call is made.
    """
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        async with app.router.lifespan_context(app):
            yield ac


# ─────────────────────────────────────────────────────────────────────────────
# 1. HAPPY PATH — authenticated GET, flag enabled, shims mocked, 200 response
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_happy_path_returns_200_composed_dashboard_response(monkeypatch):
    """Authenticated GET /api/v1/products with mocked shims → 200 + DashboardResponse.

    Asserts:
    * HTTP 200.
    * Body parses as a valid ``DashboardResponse`` shape.
    * ``products`` list has 1 item.
    * ``product_id`` equals the domain ``Product.id`` (boundary rename).
    * ``total``, ``page``, ``limit`` echo the paginated return values.
    * ``onboarding_completeness`` carries the 5-field completeness shape.

    Both shims are patched at the ``app.service`` surface (the same surface the
    service.py pipeline calls — ensures the route calls the real service and the
    service calls the patched shims, exercising the full within-service pipeline).
    """
    catalog_calls: list[dict[str, Any]] = []
    customer_calls: list[dict[str, Any]] = []

    async def _mock_list_products(*, user_id, pagination, db=None):
        catalog_calls.append({"user_id": user_id, "page": pagination.page, "limit": pagination.limit})
        return _PAGINATED_ONE

    async def _mock_get_completeness(*, user_id, db=None):
        customer_calls.append({"user_id": user_id})
        return _SAMPLE_COMPLETENESS

    monkeypatch.setattr(catalog_client, "list_products", _mock_list_products)
    monkeypatch.setattr(customer_client, "get_onboarding_completeness", _mock_get_completeness)

    app.dependency_overrides[get_current_user] = _stub_get_current_user
    app.dependency_overrides[get_db] = _noop_get_db

    try:
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            async with app.router.lifespan_context(app):
                response = await ac.get("/api/v1/products", params={"page": 1, "limit": 20})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200, (
        f"Expected 200 on happy path, got {response.status_code}: {response.text}"
    )

    body = response.json()

    # Parse through the Pydantic model to confirm wire-shape compliance.
    parsed = DashboardResponse.model_validate(body)
    assert len(parsed.products) == 1, f"Expected 1 product, got {len(parsed.products)}"

    # product_id rename: Product.id → ProductListItem.product_id
    row = parsed.products[0]
    assert row.product_id == _PRODUCT_ID, (
        f"product_id mismatch: expected {_PRODUCT_ID}, got {row.product_id}"
    )
    assert row.name == "Cotton Kurta"
    assert row.status == "ready"
    assert row.category_id == _CATEGORY_ID
    assert row.created_at == _NOW
    assert row.updated_at == _NOW

    # total / page / limit passthrough from the mocked paginated object.
    assert parsed.total == 1, f"total mismatch: expected 1, got {parsed.total}"
    assert parsed.page == 1
    assert parsed.limit == 20

    # 5-field onboarding_completeness 1:1 copy.
    oc = parsed.onboarding_completeness
    assert oc.base_complete_count == 8
    assert oc.base_total_count == 10
    assert oc.extension_complete_count == 2
    assert oc.extension_total_count == 5
    assert oc.onboarding_complete is False

    # Both shims were called exactly once.
    assert len(catalog_calls) == 1, f"catalog shim called {len(catalog_calls)} times (expected 1)"
    assert len(customer_calls) == 1, f"customer shim called {len(customer_calls)} times (expected 1)"

    # user_id forwarded to catalog shim.
    assert catalog_calls[0]["user_id"] == _STUB_USER_ID
    assert catalog_calls[0]["page"] == 1
    assert catalog_calls[0]["limit"] == 20

    # user_id forwarded to customer shim.
    assert customer_calls[0]["user_id"] == _STUB_USER_ID


@pytest.mark.asyncio
async def test_happy_path_pagination_forwarded_to_catalog_shim(monkeypatch):
    """Page/limit query params reach the catalog shim as the correct Pagination values."""
    catalog_calls: list[dict[str, Any]] = []

    async def _mock_list_products(*, user_id, pagination, db=None):
        catalog_calls.append({"page": pagination.page, "limit": pagination.limit})
        return PaginatedProductsInternal(items=(), total=0, page=pagination.page, limit=pagination.limit)

    async def _mock_get_completeness(*, user_id, db=None):
        return _SAMPLE_COMPLETENESS

    monkeypatch.setattr(catalog_client, "list_products", _mock_list_products)
    monkeypatch.setattr(customer_client, "get_onboarding_completeness", _mock_get_completeness)

    app.dependency_overrides[get_current_user] = _stub_get_current_user
    app.dependency_overrides[get_db] = _noop_get_db

    try:
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            async with app.router.lifespan_context(app):
                response = await ac.get("/api/v1/products", params={"page": 3, "limit": 50})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 3
    assert body["limit"] == 50

    assert len(catalog_calls) == 1
    assert catalog_calls[0]["page"] == 3
    assert catalog_calls[0]["limit"] == 50


# ─────────────────────────────────────────────────────────────────────────────
# 2. EMPTY STATE — mocked catalog returns zero items → 200 NOT 404
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_empty_inventory_returns_200_with_empty_products_list(monkeypatch):
    """Zero products from the catalog shim → 200 with ``products: []``, ``total: 0``.

    Empty inventory is a valid first-time-seller state — the router MUST NOT
    return 404 (§13.B lock, validated against the monolith test_empty_state.py).
    """
    async def _mock_list_products(*, user_id, pagination, db=None):
        return _PAGINATED_ZERO

    async def _mock_get_completeness(*, user_id, db=None):
        return ProfileCompleteness(
            base_complete_count=0,
            base_total_count=10,
            extension_complete_count=0,
            extension_total_count=0,
            onboarding_complete=False,
        )

    monkeypatch.setattr(catalog_client, "list_products", _mock_list_products)
    monkeypatch.setattr(customer_client, "get_onboarding_completeness", _mock_get_completeness)

    app.dependency_overrides[get_current_user] = _stub_get_current_user
    app.dependency_overrides[get_db] = _noop_get_db

    try:
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            async with app.router.lifespan_context(app):
                response = await ac.get("/api/v1/products", params={"page": 1, "limit": 20})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200, (
        f"Empty inventory must return 200, NOT 404. Got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body["products"] == [], (
        f"Expected empty products list, got: {body.get('products')}"
    )
    assert body["total"] == 0, f"Expected total=0, got {body.get('total')}"
    assert body["page"] == 1
    assert body["limit"] == 20

    # onboarding_completeness still surfaces even for a zero-product seller.
    oc = body["onboarding_completeness"]
    assert oc["base_total_count"] == 10  # denominator always surfaces
    assert oc["onboarding_complete"] is False


@pytest.mark.asyncio
async def test_empty_inventory_high_page_number_returns_200_not_404(monkeypatch):
    """GET /api/v1/products?page=100 on a zero-product seller → 200, NOT 404.

    Being past-the-end on pagination is not an error state (§13.B + monolith
    test_empty_state.py test_empty_state_with_high_page_number_does_not_404).
    """
    async def _mock_list_products(*, user_id, pagination, db=None):
        return PaginatedProductsInternal(
            items=(), total=0, page=pagination.page, limit=pagination.limit
        )

    async def _mock_get_completeness(*, user_id, db=None):
        return _SAMPLE_COMPLETENESS

    monkeypatch.setattr(catalog_client, "list_products", _mock_list_products)
    monkeypatch.setattr(customer_client, "get_onboarding_completeness", _mock_get_completeness)

    app.dependency_overrides[get_current_user] = _stub_get_current_user
    app.dependency_overrides[get_db] = _noop_get_db

    try:
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            async with app.router.lifespan_context(app):
                response = await ac.get("/api/v1/products", params={"page": 100, "limit": 20})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    body = response.json()
    assert body["products"] == []
    assert body["total"] == 0
    assert body["page"] == 100  # echoes the request
    assert body["limit"] == 20


# ─────────────────────────────────────────────────────────────────────────────
# 3. FEATURE-FLAG 404 — flag disabled → 404 BEFORE any shim call
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_feature_flag_disabled_returns_404_and_no_shim_called(stub_client):
    """FEATURE_TRACKING_DASHBOARD_ENABLED=false → 404 with locked detail string.

    The shim explodes if called — proves the 404 guard fires BEFORE the service
    call, not after it. Matches D3 kill-switch semantics: the read IS the feature.
    (Ported from monolith test_feature_flag.py + test_dashboard_extraction.py.)
    """
    shim_reached = {"catalog": False, "customer": False}

    async def _exploding_list_products(**_):  # pragma: no cover — must NOT be called
        shim_reached["catalog"] = True
        raise AssertionError("catalog shim called despite flag=False")

    async def _exploding_get_completeness(**_):  # pragma: no cover
        shim_reached["customer"] = True
        raise AssertionError("customer shim called despite flag=False")

    with (
        patch("app.router.settings") as mock_settings,
        patch.object(catalog_client, "list_products", _exploding_list_products),
        patch.object(customer_client, "get_onboarding_completeness", _exploding_get_completeness),
    ):
        mock_settings.FEATURE_TRACKING_DASHBOARD_ENABLED = False

        response = await stub_client.get("/api/v1/products", params={"page": 1, "limit": 20})

    assert response.status_code == 404, (
        f"Expected 404 when flag is disabled, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body.get("detail") == "Tracking Dashboard is disabled in this environment", (
        f"Unexpected detail: {body.get('detail')!r}"
    )

    # Neither shim was reached.
    assert not shim_reached["catalog"], "catalog shim was called despite flag=False"
    assert not shim_reached["customer"], "customer shim was called despite flag=False"


@pytest.mark.asyncio
async def test_feature_flag_disabled_response_is_json(stub_client):
    """Flag-disabled 404 produces a valid JSON body with 'detail' key.

    FastAPI's HTTPException handler emits ``{"detail": "..."}`` — confirms this
    is not a plain-text or HTML error page (ported from monolith test_feature_flag.py).
    """
    with patch("app.router.settings") as mock_settings:
        mock_settings.FEATURE_TRACKING_DASHBOARD_ENABLED = False

        response = await stub_client.get("/api/v1/products")

    assert response.status_code == 404
    body = response.json()
    assert isinstance(body, dict), f"Response body is not a JSON object: {response.text}"
    assert "detail" in body, f"Response body missing 'detail' key: {body}"


# ─────────────────────────────────────────────────────────────────────────────
# 4. PAGINATION VALIDATION — 422 BEFORE any shim call
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_pagination_page_zero_returns_422(stub_client):
    """``page=0`` violates the ``ge=1`` Query constraint → 422 before any shim call.

    FastAPI's Query validator rejects the parameter at the route layer — the
    service/shim is never invoked. (Ported from monolith test_pagination_validation.py.)
    """
    response = await stub_client.get("/api/v1/products", params={"page": 0, "limit": 20})

    assert response.status_code == 422, (
        f"Expected 422 for page=0, got {response.status_code}: {response.text}"
    )
    body = response.json()
    # The §4.F error handler emits {"detail": str, "errors": [{field, constraint, msg}, ...]}
    assert "detail" in body, f"422 body missing 'detail': {body}"
    # Confirm the 'page' field is referenced — either in the errors list or in the detail string.
    errors = body.get("errors", [])
    page_mentioned = (
        any(e.get("field") == "page" for e in errors)
        or "page" in str(body.get("detail", ""))
    )
    assert page_mentioned, (
        f"Expected validation error referencing 'page'; body: {body}"
    )


@pytest.mark.asyncio
async def test_pagination_limit_zero_returns_422(stub_client):
    """``limit=0`` violates the ``ge=1`` Query constraint → 422."""
    response = await stub_client.get("/api/v1/products", params={"page": 1, "limit": 0})

    assert response.status_code == 422, (
        f"Expected 422 for limit=0, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "detail" in body, f"422 body missing 'detail': {body}"
    errors = body.get("errors", [])
    limit_mentioned = (
        any(e.get("field") == "limit" for e in errors)
        or "limit" in str(body.get("detail", ""))
    )
    assert limit_mentioned, (
        f"Expected validation error referencing 'limit'; body: {body}"
    )


@pytest.mark.asyncio
async def test_pagination_limit_101_returns_422(stub_client):
    """``limit=101`` violates the ``le=100`` Query constraint → 422."""
    response = await stub_client.get("/api/v1/products", params={"page": 1, "limit": 101})

    assert response.status_code == 422, (
        f"Expected 422 for limit=101, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "detail" in body, f"422 body missing 'detail': {body}"
    errors = body.get("errors", [])
    limit_mentioned = (
        any(e.get("field") == "limit" for e in errors)
        or "limit" in str(body.get("detail", ""))
    )
    assert limit_mentioned, (
        f"Expected validation error referencing 'limit'; body: {body}"
    )


@pytest.mark.asyncio
async def test_pagination_valid_boundary_limit_100_accepted(monkeypatch):
    """``limit=100`` is the maximum valid value — must NOT return 422.

    Counter-proof to the limit=101 rejection test. Verifies the Pydantic
    ``le=100`` constraint is inclusive (monolith test_pagination_validation.py
    test_page_1_and_limit_100_max_boundary_accepted).
    """
    async def _mock_list_products(*, user_id, pagination, db=None):
        return PaginatedProductsInternal(items=(), total=0, page=1, limit=pagination.limit)

    async def _mock_get_completeness(*, user_id, db=None):
        return _SAMPLE_COMPLETENESS

    monkeypatch.setattr(catalog_client, "list_products", _mock_list_products)
    monkeypatch.setattr(customer_client, "get_onboarding_completeness", _mock_get_completeness)

    app.dependency_overrides[get_current_user] = _stub_get_current_user
    app.dependency_overrides[get_db] = _noop_get_db

    try:
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            async with app.router.lifespan_context(app):
                response = await ac.get("/api/v1/products", params={"page": 1, "limit": 100})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200, (
        f"limit=100 must be accepted (le=100 is inclusive), got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body["limit"] == 100


# ─────────────────────────────────────────────────────────────────────────────
# 5. AUTH — unauthenticated request → 401/403
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401_or_403(unauth_client):
    """No Bearer token → TokenMissingError (401) or UserNotFoundError (403).

    svc-dashboard's ``get_current_user`` raises ``TokenMissingError`` (401) when
    no Authorization header is present. The exact status code depends on the
    vendored ``core/auth.py`` implementation.

    No service/shim call is made — auth rejection is a pre-route dependency.
    (Mirrors svc-export's unauthenticated-request test.)
    """
    response = await unauth_client.get("/api/v1/products", params={"page": 1, "limit": 20})

    assert response.status_code in {401, 403}, (
        f"Expected 401 or 403 for unauthenticated request, "
        f"got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "detail" in body, f"Auth rejection response missing 'detail': {body}"
