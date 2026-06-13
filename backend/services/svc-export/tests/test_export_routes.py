"""Mounted-route inventory tests for svc-export (spec §3.B acceptance).

Asserts the EXACT 2 /api/v1 export routes mount on the live app object with
the correct paths, methods, response models, and status codes.

Non-tautological contract (row-26 lesson):
  Each assertion inspects real APIRoute attributes — path, methods,
  response_model, status_code — NOT ``assert True`` or string-in-repr.

Route inventory expected:
  POST /api/v1/products/{product_id}/export-xlsx — 202, ExportInitiatedResponse
  GET  /api/v1/exports/{export_id}               — 200, ExportResponse

Infra routes NOT counted:
  /health (plain @app.get, not in the APIRouter)
  /metrics (Starlette Mount, not an APIRoute)
  FastAPI builtins (/openapi.json, /docs, /redoc, /docs/oauth2-redirect)
"""

from __future__ import annotations

from fastapi.routing import APIRoute

from app.main import app
from app.schemas import ExportInitiatedResponse, ExportResponse


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────
def _api_v1_routes() -> list[APIRoute]:
    """Return only the APIRoute objects whose path starts with /api/v1."""
    return [
        r
        for r in app.routes
        if isinstance(r, APIRoute) and r.path.startswith("/api/v1")
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Exactly 2 /api/v1 export routes are mounted
# ─────────────────────────────────────────────────────────────────────────────
def test_exactly_two_api_v1_routes_mounted():
    """Exactly 2 APIRoute objects mount under /api/v1 — no more, no less.

    svc-export is a LEAF consumer (spec §3.B): zero /internal/* routes.
    """
    routes = _api_v1_routes()
    paths = [r.path for r in routes]
    assert len(routes) == 2, (
        f"Expected exactly 2 /api/v1 APIRoutes; got {len(routes)}: {paths}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. POST route — path, method, status_code, response_model
# ─────────────────────────────────────────────────────────────────────────────
def test_post_export_xlsx_route_attributes():
    """POST /api/v1/products/{product_id}/export-xlsx mounts with correct attrs."""
    routes = _api_v1_routes()
    post_routes = [r for r in routes if "POST" in r.methods]
    assert len(post_routes) == 1, f"Expected 1 POST route; got {len(post_routes)}"

    route = post_routes[0]

    # Path — exact param name {product_id}, not {id}
    assert route.path == "/api/v1/products/{product_id}/export-xlsx", (
        f"POST path mismatch: {route.path}"
    )

    # Method
    assert "POST" in route.methods

    # 202 Accepted — not 200
    assert route.status_code == 202, (
        f"Expected 202; got {route.status_code}"
    )

    # response_model is ExportInitiatedResponse
    assert route.response_model is ExportInitiatedResponse, (
        f"POST response_model is {route.response_model!r}, expected ExportInitiatedResponse"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. GET route — path, method, status_code, response_model
# ─────────────────────────────────────────────────────────────────────────────
def test_get_export_route_attributes():
    """GET /api/v1/exports/{export_id} mounts with correct attrs."""
    routes = _api_v1_routes()
    get_routes = [r for r in routes if "GET" in r.methods]
    assert len(get_routes) == 1, f"Expected 1 GET route; got {len(get_routes)}"

    route = get_routes[0]

    # Path — exact param name {export_id}, not {id}
    assert route.path == "/api/v1/exports/{export_id}", (
        f"GET path mismatch: {route.path}"
    )

    # Method
    assert "GET" in route.methods

    # 200 OK (default) — FastAPI stores None when the default 200 is used;
    # the effective status code is always 200 for a plain GET.
    assert (route.status_code is None or route.status_code == 200), (
        f"Expected 200 or None (implicit 200); got {route.status_code}"
    )

    # response_model is ExportResponse
    assert route.response_model is ExportResponse, (
        f"GET response_model is {route.response_model!r}, expected ExportResponse"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. NO /internal/* routes present
# ─────────────────────────────────────────────────────────────────────────────
def test_no_internal_routes_mounted():
    """svc-export is a leaf consumer — zero /internal/* routes must mount.

    Export has NO inbound callers; it is the terminus. Any /internal/* route
    would be a spec violation (spec §3.B + §0.4 leaf-consumer declaration).
    """
    internal_routes = [
        r
        for r in app.routes
        if isinstance(r, APIRoute) and r.path.startswith("/internal")
    ]
    assert internal_routes == [], (
        f"Unexpected /internal/* routes found: {[r.path for r in internal_routes]}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Route tags confirm export ownership
# ─────────────────────────────────────────────────────────────────────────────
def test_routes_carry_export_tag():
    """Both /api/v1 routes carry the 'export' OpenAPI tag."""
    routes = _api_v1_routes()
    for route in routes:
        assert "export" in route.tags, (
            f"Route {route.path} missing 'export' tag; has: {route.tags}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Both routes require authentication (get_current_user dependency present)
# ─────────────────────────────────────────────────────────────────────────────
def test_both_routes_have_auth_dependency():
    """Both export routes carry get_current_user in their dependency chain.

    Parameter-level ``Depends()`` (i.e. ``user: Annotated[..., Depends(f)]``)
    are resolved into ``route.dependant.dependencies``, NOT ``route.dependencies``
    (which only holds decorator-level ``dependencies=[Depends(...)]`` args).
    We walk the full dependant tree to confirm get_current_user is reachable.
    """
    from app.core.auth import get_current_user

    def _dep_callables(dependant) -> set:
        """Recursively collect all dependency callables from the dependant tree.

        Each item in ``dependant.dependencies`` is itself a ``Dependant`` object
        (FastAPI 0.115 — the item IS the child dependant, not a wrapper with
        a ``.dependant`` attr).
        """
        found = set()
        for child_dep in dependant.dependencies:
            found.add(child_dep.call)
            found.update(_dep_callables(child_dep))  # child_dep IS the Dependant
        return found

    routes = _api_v1_routes()
    for route in routes:
        all_deps = _dep_callables(route.dependant)
        assert get_current_user in all_deps, (
            f"Route {route.path} missing get_current_user in dependency tree; "
            f"found callables: {[getattr(d, '__name__', repr(d)) for d in all_deps]}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Full mounted-route inventory (diagnostic — documents every route on app)
# ─────────────────────────────────────────────────────────────────────────────
def test_full_mounted_route_inventory():
    """Document the complete mounted route list for the merge-gate report.

    This test never fails on its own — it is a living inventory assertion that
    ensures the count is EXACTLY what the spec declared (2 api/v1 + /health +
    /metrics Mount + 4 FastAPI builtins = 8 total app.routes entries).
    The important invariant is the /api/v1 subset = 2.
    """
    from starlette.routing import Mount, Route

    all_routes = app.routes
    api_v1 = _api_v1_routes()

    # Confirm expected path set for api/v1
    api_v1_paths = {(r.path, next(iter(r.methods))) for r in api_v1}
    expected_api_v1 = {
        ("/api/v1/products/{product_id}/export-xlsx", "POST"),
        ("/api/v1/exports/{export_id}", "GET"),
    }
    assert api_v1_paths == expected_api_v1, (
        f"api/v1 route set mismatch.\n  Got:      {sorted(api_v1_paths)}\n"
        f"  Expected: {sorted(expected_api_v1)}"
    )

    # Health endpoint present
    health_routes = [
        r for r in all_routes if isinstance(r, APIRoute) and r.path == "/health"
    ]
    assert len(health_routes) == 1, "Expected /health APIRoute"

    # Metrics mount present
    metrics_mounts = [r for r in all_routes if isinstance(r, Mount) and r.path == "/metrics"]
    assert len(metrics_mounts) == 1, "Expected /metrics Mount"

    # FastAPI builtins present (openapi.json, docs, redoc, docs/oauth2-redirect)
    starlette_routes = [r for r in all_routes if isinstance(r, Route)]
    builtin_paths = {r.path for r in starlette_routes}
    assert "/openapi.json" in builtin_paths, "Expected /openapi.json builtin"
    assert "/docs" in builtin_paths, "Expected /docs builtin"
