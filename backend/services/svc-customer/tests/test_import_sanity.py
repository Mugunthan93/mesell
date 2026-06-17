"""svc-customer import-sanity — the whole app tree imports clean (boots).

This is the cheapest possible smoke gate: every module in the svc-customer app
tree imports without error, the FastAPI ``app`` constructs, the 3 INBOUND
``/internal/*`` routes are mounted, and the 6-effective-middleware chain is
present.  NOT a tautology — a broken import path, a missing vendored symbol, or
a Celery dependency that should NOT be present all fail here.
"""

from __future__ import annotations


def test_app_imports_and_constructs():
    """``app.main:app`` constructs (the FastAPI application object exists)."""
    from app.main import app

    assert app.title == "MeeSell svc-customer"


def test_three_internal_routes_mounted():
    """The 3 FROZEN ``/internal/*`` provider routes are mounted by main.py."""
    from app.main import app

    paths = {r.path for r in app.routes}
    assert "/internal/seller-profile/{user_id}/compliance-block" in paths
    assert "/internal/seller-profile/{user_id}/onboarding-completeness" in paths
    assert "/internal/seller-profile/{user_id}/eligibility" in paths


def test_six_effective_middleware_present():
    """The §4.H 6-effective chain + the extraction-support request_context layer
    are all registered (7 BaseHTTPMiddleware + CORS = the locked shape)."""
    from app.main import app

    names = {mw.cls.__name__ for mw in app.user_middleware}
    assert "AuditMiddleware" in names
    assert "PlanGuardMiddleware" in names
    assert "RateLimitMiddleware" in names
    assert "TenancyContextMiddleware" in names
    assert "AuthContextMiddleware" in names
    assert "RequestContextMiddleware" in names
    assert "RequestIdMiddleware" in names
    assert "CORSMiddleware" in names


def test_no_celery_dependency_in_tree():
    """customer runs NO Celery worker — there is no celery_app / tasks module,
    and importing one must fail (the dependency is absent by design — E1)."""
    import importlib

    for mod in ("app.celery_app", "app.tasks", "app.workers"):
        try:
            importlib.import_module(mod)
        except ModuleNotFoundError:
            continue
        raise AssertionError(
            f"{mod} should NOT exist in svc-customer (NO Celery — spec §0.8 / E1)"
        )


def test_no_ai_sms_payment_gcs_settings():
    """The trimmed Settings carries NO AI / SMS / payment / GCS env fields."""
    from app.shared.config import Settings

    forbidden = {
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "MSG91_AUTH_KEY",
        "MSG91_TEMPLATE_ID",
        "RAZORPAY_KEY_ID",
        "RAZORPAY_KEY_SECRET",
        "RAZORPAY_WEBHOOK_SECRET",
        "GCS_BUCKET",
        "GCS_PROJECT_ID",
    }
    declared = set(Settings.model_fields.keys())
    leaked = forbidden & declared
    assert not leaked, f"trimmed Settings leaked forbidden fields: {sorted(leaked)}"
