"""Import-sanity — the svc-dashboard tree imports clean (spec acceptance).

Mirrors ``svc-export/tests/test_import_sanity.py`` (SP01) adapted to the
dashboard service characteristics:

* svc-dashboard is a PURE READ — NO Celery broker, NO Celery worker, no
  ``celery_app`` module, no ``tasks`` module.
* Trimmed Settings carries NONE of the AI / SMS / payment / GCS / Langfuse /
  refresh-token keys (the dashboard only needs DATABASE_URL, VALKEY_URL,
  JWT_SECRET, AUDIT_PII_SALT, CORS_ALLOWED_ORIGINS, MONOLITH_INTERNAL_BASE_URL,
  APP_ENV).
* Exactly 1 business ``/api/v1`` APIRoute is mounted (``GET /api/v1/products``).

These four tests prove the extraction is boot-safe as a standalone deployment:
a broken import path or a leaked Settings field would be caught at ``pytest``
collection time (before any live infra is needed), failing the merge gate early.
"""

from __future__ import annotations

import sys


# ─────────────────────────────────────────────────────────────────────────────
# 1. app.main imports clean and has the expected app title + /health route
# ─────────────────────────────────────────────────────────────────────────────
def test_app_main_imports_clean():
    """``app.main`` imports without error; the dashboard router is mounted.

    Confirms the full import chain — config singleton load, 6-middleware chain,
    error handlers, extracted_clients shims, service, router — boots cleanly.
    The app title is the service-specific string set in ``main.py``.
    """
    from app.main import app

    assert app.title == "MeeSell svc-dashboard", (
        f"app.title mismatch: expected 'MeeSell svc-dashboard', got {app.title!r}"
    )
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/health" in paths, f"/health route missing; all routes: {paths}"
    assert "/api/v1/products" in paths, (
        f"GET /api/v1/products missing; all routes: {paths}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Service + shim imports resolve and the shim aliases are correct
# ─────────────────────────────────────────────────────────────────────────────
def test_service_imports_and_shim_aliases_resolve():
    """``app.service`` imports; the 2 extracted_clients aliases resolve correctly.

    The 2 cross-module shims re-export the SAME symbol names as the monolith
    in-process imports (§16.G) so the call sites in ``service.py`` are unchanged.
    """
    from app import service
    from app.core.extracted_clients import catalog_client, customer_client

    # catalog_service alias points at catalog_client (not some other module).
    assert service.catalog_service is catalog_client, (
        f"service.catalog_service should be catalog_client, got {service.catalog_service!r}"
    )
    # customer_service alias points at customer_client.
    assert service.customer_service is customer_client, (
        f"service.customer_service should be customer_client, got {service.customer_service!r}"
    )
    # The 2 shimmed methods exist.
    assert hasattr(service.catalog_service, "list_products"), (
        "catalog_client missing list_products"
    )
    assert hasattr(service.customer_service, "get_onboarding_completeness"), (
        "customer_client missing get_onboarding_completeness"
    )
    # The public service method and the private compose helper are present.
    assert hasattr(service, "list_products_for_dashboard"), (
        "service.list_products_for_dashboard missing"
    )
    assert hasattr(service, "_compose_response"), (
        "service._compose_response missing (required by extraction tests)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. NO Celery in sys.modules after boot
# ─────────────────────────────────────────────────────────────────────────────
def test_no_celery_in_sys_modules_after_boot():
    """svc-dashboard is a pure read — NO Celery broker/worker should be imported.

    The monolith registers a Celery app and tasks; svc-dashboard MUST NOT carry
    those dependencies (they imply a broker connection on boot and an unexpected
    worker queue).  If ``celery`` appears in sys.modules after importing
    ``app.main``, a dependency has leaked the Celery import chain.

    Relies on the fact that ``app.main`` was already imported by test #1 above,
    so sys.modules reflects the full boot import graph.
    """
    from app.main import app  # noqa: F401 — ensures the full boot graph is loaded

    assert "celery" not in sys.modules, (
        "celery is in sys.modules after svc-dashboard boot — "
        "a dependency has leaked the Celery import chain. "
        "svc-dashboard is a pure read and must run NO Celery worker."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Trimmed Settings carries NO AI / SMS / payment / GCS / Langfuse keys
# ─────────────────────────────────────────────────────────────────────────────
def test_trimmed_settings_has_no_ai_sms_payment_gcs_vars():
    """Trimmed Settings carries NONE of the monolith's AI/SMS/payment/GCS fields.

    svc-dashboard is a pure read with no AI text generation, no SMS OTPs, no
    payment processing, and no direct GCS access (images are served via the
    catalog shim's signed URLs).  Leaking any of these fields would imply the
    service has unnecessary secret requirements at boot — a security and
    operational surface increase that is not permitted.
    """
    from app.shared.config import Settings

    field_names = set(Settings.model_fields.keys())
    forbidden = {
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_HOST",
        "MSG91_AUTH_KEY",
        "MSG91_TEMPLATE_ID",
        "RAZORPAY_KEY_ID",
        "RAZORPAY_KEY_SECRET",
        "RAZORPAY_WEBHOOK_SECRET",
        "GCS_BUCKET",
        "GCS_PROJECT_ID",
        "AI_DAILY_BUDGET_INR",
        "AI_BUDGET_ALARM_THRESHOLD",
        "REFRESH_TOKEN_PEPPER",
    }
    leaked = field_names & forbidden
    assert not leaked, (
        f"trimmed Settings leaked AI/SMS/payment/GCS vars: {leaked!r} — "
        "these fields must be removed from svc-dashboard's Settings class."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Exactly 1 business /api/v1 APIRoute is mounted (GET /api/v1/products)
# ─────────────────────────────────────────────────────────────────────────────
def test_exactly_one_api_v1_business_route_mounted():
    """Exactly 1 business ``/api/v1`` APIRoute is mounted: GET /api/v1/products.

    svc-dashboard is a leaf consumer (§3.B):
    * Zero /internal/* routes (no inbound callers).
    * Zero extra /api/v1 routes (dashboard owns only 1 endpoint in V1).

    This is the structural invariant that prevents route-count drift in future
    sessions accidentally adding a second route to the svc tree.
    """
    from fastapi.routing import APIRoute

    from app.main import app

    api_v1_routes = [
        r
        for r in app.routes
        if isinstance(r, APIRoute) and r.path.startswith("/api/v1")
    ]

    assert len(api_v1_routes) == 1, (
        f"Expected exactly 1 /api/v1 APIRoute; got {len(api_v1_routes)}: "
        f"{[r.path for r in api_v1_routes]}"
    )

    route = api_v1_routes[0]
    assert route.path == "/api/v1/products", (
        f"Expected /api/v1/products, got {route.path}"
    )
    assert "GET" in route.methods, (
        f"Expected GET method, got {route.methods}"
    )

    # Confirm NO /internal/* routes.
    internal_routes = [
        r
        for r in app.routes
        if isinstance(r, APIRoute) and r.path.startswith("/internal")
    ]
    assert internal_routes == [], (
        f"Unexpected /internal/* routes: {[r.path for r in internal_routes]}"
    )
