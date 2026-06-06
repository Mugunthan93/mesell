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

    Allowed set (updated for §7 iam construction):
      FastAPI builtins: /openapi.json, /docs, /docs/oauth2-redirect, /redoc
      §7 iam routes:
        POST /api/v1/auth/otp/send
        POST /api/v1/auth/otp/verify
        POST /api/v1/auth/refresh        (FE-D5 amendment)
        POST /api/v1/auth/logout         (FE-D5 amendment)
        GET  /api/v1/auth/me
        POST /api/v1/webhooks/razorpay
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
        "/health",
    }
    route_map = _route_map(meesell_app)
    stray = set(route_map) - allowed_paths
    assert not stray, (
        f"Stray routes detected — legacy router(s) not removed: {sorted(stray)}"
    )


def test_total_route_count(meesell_app):
    """Exact route count: 11 routable entries
    (FastAPI builtins x4 + §7 iam x6 + health x1).

    Breakdown:
      FastAPI builtins: /openapi.json, /docs, /docs/oauth2-redirect, /redoc  (4)
      §7 iam:           /api/v1/auth/otp/send, /api/v1/auth/otp/verify,
                        /api/v1/auth/refresh, /api/v1/auth/logout,
                        /api/v1/auth/me, /api/v1/webhooks/razorpay         (6)
      Health:           /health                                              (1)
    Total = 11

    If this fails, a route was added or removed unexpectedly.
    """
    route_map = _route_map(meesell_app)
    expected_count = 11
    assert len(route_map) == expected_count, (
        f"Expected {expected_count} routes, got {len(route_map)}. "
        f"Paths: {sorted(route_map)}"
    )
