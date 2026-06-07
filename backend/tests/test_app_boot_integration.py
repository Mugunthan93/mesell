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

    Allowed set (updated for §9 category construction):
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
        "/health",
    }
    route_map = _route_map(meesell_app)
    stray = set(route_map) - allowed_paths
    assert not stray, (
        f"Stray routes detected — legacy router(s) not removed: {sorted(stray)}"
    )


def test_total_route_count(meesell_app):
    """Exact route count: 20 distinct path entries in the route_map
    (FastAPI builtins x4 + §7 iam x6 + §8 customer x4 paths + §9 category x5 + health x1).

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
      Health:           /health                                                 (1)
    Total = 20 distinct paths

    Note: FastAPI creates one APIRoute object per (path, method) combination, so
    /api/v1/seller-profile has 2 APIRoute objects (GET + PATCH) but the _route_map()
    helper deduplicates by path key → 1 entry.

    If this fails, a route was added or removed unexpectedly.
    """
    route_map = _route_map(meesell_app)
    expected_count = 20
    assert len(route_map) == expected_count, (
        f"Expected {expected_count} routes, got {len(route_map)}. "
        f"Paths: {sorted(route_map)}"
    )
