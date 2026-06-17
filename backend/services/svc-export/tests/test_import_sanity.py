"""Import-sanity — the svc-export tree imports clean (spec acceptance).

``app.main`` import pulls in the whole vendored chain (config singleton load,
6-mw, error handlers, the extracted_clients shims, the service/tasks/repository/
domain/exceptions modules).  If any vendored import path is wrong, this fails.
"""

from __future__ import annotations


def test_app_main_imports_clean():
    """app.main imports without error (router mount is import-tolerant)."""
    from app.main import app

    assert app.title == "MeeSell svc-export"
    # /health + /metrics mount are present even before app.router lands.
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/health" in paths


def test_service_imports_and_callsites_resolve():
    """The byte-for-byte service module imports; the 4 shim aliases resolve to
    the extracted_clients modules (re-exported symbol names intact).
    """
    from app import service

    # The 4 cross-module aliases are bound to the shim modules.
    assert service.catalog_service.__name__.endswith("catalog_client")
    assert service.category_service.__name__.endswith("category_client")
    assert service.customer_service.__name__.endswith("customer_client")
    assert service.image_service.__name__.endswith("image_client")
    # The 6 shimmed methods are present on the aliases.
    assert hasattr(service.catalog_service, "assert_product_ownership")
    assert hasattr(service.catalog_service, "get_product_for_export")
    assert hasattr(service.category_service, "fetch_schema")
    assert hasattr(service.category_service, "get_field_enum")
    assert hasattr(service.customer_service, "get_compliance_block")
    assert hasattr(service.image_service, "list_images")


def test_tasks_module_imports_and_task_name():
    """The Celery task imports and keeps ``name='export.xlsx'``."""
    from app.tasks import export_xlsx_task

    assert export_xlsx_task.name == "export.xlsx"


def test_celery_app_config():
    """celery_app: single task module, svc-export queue, DB1/DB2, key prefix."""
    from app.celery_app import BROKER_URL, RESULT_BACKEND_URL, celery_app

    assert celery_app.conf.include == ["app.tasks"]
    assert celery_app.conf.task_default_queue == "svc-export"
    assert celery_app.conf.task_routes == {"export.xlsx": {"queue": "svc-export"}}
    assert BROKER_URL.endswith("/1")  # broker = Valkey DB 1
    assert RESULT_BACKEND_URL.endswith("/2")  # results = Valkey DB 2
    assert celery_app.conf.broker_transport_options["global_keyprefix"] == "svc-export:"
    assert (
        celery_app.conf.result_backend_transport_options["global_keyprefix"]
        == "svc-export:"
    )
    # Locked worker invariants.
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1


def test_trimmed_settings_has_no_ai_sms_payment_vars():
    """Trimmed Settings carries NO gemini/langfuse/msg91/razorpay fields."""
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
        "AI_DAILY_BUDGET_INR",
        "AI_BUDGET_ALARM_THRESHOLD",
        "REFRESH_TOKEN_PEPPER",
    }
    leaked = field_names & forbidden
    assert not leaked, f"trimmed Settings leaked AI/SMS/payment vars: {leaked}"
