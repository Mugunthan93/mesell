"""Boot integration test: verifies app.main imports cleanly and only the
expected routes are mounted (no stray legacy routers).

Acceptance criteria (per coordinator brief):
- `from app.main import app` succeeds with no ImportError.
- `app` is a FastAPI instance.
- Exactly the two V1 auth POST routes are mounted under /api/v1/auth/.
- FastAPI built-in routes (OpenAPI + docs + redoc) and the /health route
  are present.
- No other application routes exist (no stray legacy router survives).
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Route

pytestmark = pytest.mark.smoke


# ---------------------------------------------------------------------------
# Fixture: import the app once per session to catch ImportError at the top.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def meesell_app():
    """Import and return the FastAPI app.

    Any ImportError here produces a clear failure at the fixture level rather
    than an obscure AttributeError inside a test.
    """
    from app.main import app  # noqa: PLC0415
    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_routable(app: FastAPI) -> list[Route | APIRoute]:
    """Return Route and APIRoute instances (excludes Mount objects).

    FastAPI mounts its built-in OpenAPI routes as starlette.routing.Route,
    while application endpoints are fastapi.routing.APIRoute.  Both have
    .path and .methods attributes.
    """
    return [r for r in app.routes if isinstance(r, (Route, APIRoute))]


def _route_map(app: FastAPI) -> dict[str, set[str]]:
    """Return {path: {methods}} for all routable endpoints."""
    result: dict[str, set[str]] = {}
    for r in _all_routable(app):
        result[r.path] = set(r.methods or [])
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_app_is_fastapi_instance(meesell_app):
    """app must be a FastAPI instance."""
    assert isinstance(meesell_app, FastAPI), (
        f"Expected FastAPI instance, got {type(meesell_app)}"
    )


def test_otp_send_route_mounted(meesell_app):
    """POST /api/v1/auth/otp/send must be mounted."""
    route_map = _route_map(meesell_app)
    path = "/api/v1/auth/otp/send"
    assert path in route_map, (
        f"Route {path!r} not found. Mounted paths: {sorted(route_map)}"
    )
    assert "POST" in route_map[path], (
        f"Expected POST on {path!r}, got {route_map[path]}"
    )


def test_otp_verify_route_mounted(meesell_app):
    """POST /api/v1/auth/otp/verify must be mounted."""
    route_map = _route_map(meesell_app)
    path = "/api/v1/auth/otp/verify"
    assert path in route_map, (
        f"Route {path!r} not found. Mounted paths: {sorted(route_map)}"
    )
    assert "POST" in route_map[path], (
        f"Expected POST on {path!r}, got {route_map[path]}"
    )


def test_fastapi_builtins_present(meesell_app):
    """FastAPI built-in routes must be present."""
    route_map = _route_map(meesell_app)
    for path in ("/openapi.json", "/docs", "/redoc"):
        assert path in route_map, (
            f"Expected FastAPI built-in {path!r} to be mounted. "
            f"Mounted paths: {sorted(route_map)}"
        )


def test_health_route_present(meesell_app):
    """GET /health must be mounted."""
    route_map = _route_map(meesell_app)
    assert "/health" in route_map, (
        f"Expected /health route. Mounted paths: {sorted(route_map)}"
    )
    assert "GET" in route_map["/health"], (
        f"Expected GET on /health, got {route_map['/health']}"
    )


def test_no_stray_legacy_routes(meesell_app):
    """No route outside the allowed set must be mounted.

    Allowed set (updated for §14 export construction):
      FastAPI builtins: /openapi.json, /docs, /docs/oauth2-redirect, /redoc
      §7 iam routes:
        POST /api/v1/auth/otp/send
        POST /api/v1/auth/otp/verify
        POST /api/v1/auth/refresh        (FE-D5 amendment)
        POST /api/v1/auth/logout         (FE-D5 amendment)
        GET  /api/v1/auth/me
        POST /api/v1/webhooks/razorpay
      §8 customer routes:
        GET   /api/v1/seller-profile
        PATCH /api/v1/seller-profile
        PATCH /api/v1/seller-profile/active-categories
        PATCH /api/v1/seller-profile/compliance/{super_id}
        GET   /api/v1/seller-profile/required-fields
      §9 category routes:
        GET /api/v1/categories/suggest
        GET /api/v1/categories/browse
        GET /api/v1/categories
        GET /api/v1/categories/{id}/schema
        GET /api/v1/categories/{id}/field-enum/{name}
      §10 catalog + §13 dashboard share routes:
        POST   /api/v1/products                     (§10 catalog: create)
        GET    /api/v1/products                     (§13 dashboard: list — Feature 8)
        PATCH  /api/v1/products/{id}                (§10 catalog; also DELETE — shares path key)
        POST   /api/v1/products/{id}/autofill       (§10 catalog)
        GET    /api/v1/products/{id}/preview        (§10 catalog)
        GET    /api/v1/products/{id}/draft          (§10 catalog)
      §11 image routes:
        GET    /api/v1/products/{id}/images        (also POST — shares path key)
      §12 pricing routes:
        POST   /api/v1/products/{id}/price-calc
      §14 export routes:
        POST   /api/v1/products/{product_id}/export-xlsx
        GET    /api/v1/exports/{export_id}
      Health: /health

    This test will catch any stray legacy router that was not deleted.
    """
    allowed_paths = {
        "/openapi.json",
        "/docs",
        "/docs/oauth2-redirect",
        "/redoc",
        "/api/v1/auth/otp/send",
        "/api/v1/auth/otp/verify",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/auth/me",
        "/api/v1/webhooks/razorpay",
        "/api/v1/seller-profile",
        "/api/v1/seller-profile/active-categories",
        "/api/v1/seller-profile/compliance/{super_id}",
        "/api/v1/seller-profile/required-fields",
        "/api/v1/categories/suggest",
        "/api/v1/categories/browse",
        "/api/v1/categories",
        "/api/v1/categories/{id}/schema",
        "/api/v1/categories/{id}/field-enum/{name}",
        "/api/v1/products",
        "/api/v1/products/{id}",
        "/api/v1/products/{id}/autofill",
        "/api/v1/products/{id}/preview",
        "/api/v1/products/{id}/draft",
        "/api/v1/products/{id}/images",
        "/api/v1/products/{id}/price-calc",
        "/api/v1/products/{product_id}/export-xlsx",
        "/api/v1/exports/{export_id}",
        "/health",
    }
    route_map = _route_map(meesell_app)
    stray = set(route_map) - allowed_paths
    assert not stray, (
        f"Stray routes detected — legacy router(s) not removed: {sorted(stray)}"
    )


def test_total_route_count(meesell_app):
    """Exact route count: 29 distinct path entries in the route_map.

    Breakdown:
      FastAPI builtins: /openapi.json, /docs, /docs/oauth2-redirect, /redoc  (4)
      §7 iam:           /api/v1/auth/otp/send, /api/v1/auth/otp/verify,
                        /api/v1/auth/refresh, /api/v1/auth/logout,
                        /api/v1/auth/me, /api/v1/webhooks/razorpay             (6)
      §8 customer:      /api/v1/seller-profile  (GET + PATCH → 1 path in route_map,
                          but 2 separate APIRoute objects in app.routes),
                        /api/v1/seller-profile/active-categories (PATCH),
                        /api/v1/seller-profile/compliance/{super_id} (PATCH),
                        /api/v1/seller-profile/required-fields (GET)           (4 distinct paths)
      §9 category:      /api/v1/categories/suggest (GET),
                        /api/v1/categories/browse (GET),
                        /api/v1/categories (GET),
                        /api/v1/categories/{id}/schema (GET),
                        /api/v1/categories/{id}/field-enum/{name} (GET)        (5 distinct paths)
      §10 catalog +     /api/v1/products (POST [§10] + GET [§13] → 1 path key),
      §13 dashboard:    /api/v1/products/{id} (PATCH + DELETE → 1 path key),
                        /api/v1/products/{id}/autofill (POST),
                        /api/v1/products/{id}/preview (GET),
                        /api/v1/products/{id}/draft (GET)                      (5 distinct paths)
      §11 image:        /api/v1/products/{id}/images (GET + POST → 1 path key) (1)
      §12 pricing:      /api/v1/products/{id}/price-calc (POST)                (1)
      §14 export:       /api/v1/products/{product_id}/export-xlsx (POST)       (1)
                        /api/v1/exports/{export_id} (GET)                      (1)
      Health:           /health                                                 (1)
    Total = 29 distinct paths  (was 27 before §14 export; +2 new path keys)

    Note: FastAPI creates one APIRoute object per (path, method) combination, so
    /api/v1/products/{id} has 2 APIRoute objects (PATCH + DELETE) but the
    _route_map() helper deduplicates by path key → 1 entry. Same applies to
    /api/v1/products which carries POST (§10 catalog) and GET (§13 dashboard)
    on a single path key. The 2 new §14 export paths are DISTINCT from
    /api/v1/products/{id} (different path templates) and each contributes +1
    to the distinct path count.

    If this fails, a route was added or removed unexpectedly.
    """
    route_map = _route_map(meesell_app)
    expected_count = 29
    assert len(route_map) == expected_count, (
        f"Expected {expected_count} routes, got {len(route_map)}. "
        f"Paths: {sorted(route_map)}"
    )


def test_dashboard_get_products_route_mounted(meesell_app):
    """GET /api/v1/products must be mounted by §13 dashboard router.

    Co-located on the same path as §10 catalog's POST /api/v1/products
    (the _route_map helper deduplicates by path, so this test inspects
    app.routes directly to confirm BOTH methods exist on the path).
    """
    path = "/api/v1/products"
    methods_on_path: set[str] = set()
    for r in _all_routable(meesell_app):
        if r.path == path:
            methods_on_path.update(r.methods or [])
    assert "GET" in methods_on_path, (
        f"Expected GET on {path!r} (§13 dashboard); methods present: {methods_on_path}"
    )
    assert "POST" in methods_on_path, (
        f"Expected POST on {path!r} (§10 catalog); methods present: {methods_on_path}"
    )
