"""conftest.py for tests/scripts/ — stub env vars so the parent conftest
can import app.shared.config.Settings without requiring live credentials.

These stubs are injected BEFORE the parent conftest tries to import app.main,
because pytest loads conftest.py files from the rootdir outward, then from the
test directory inward.  To resolve the ordering gap we use a pytest plugin hook
(``pytest_configure``) which fires before any conftest-level imports.

DB-SAFETY: This conftest does NOT connect to any database.  All tests/scripts/
tests are stdlib-only unit tests that use synthetic fixtures.
"""

from __future__ import annotations

import os


def pytest_configure(config):  # noqa: ANN001
    """Inject minimum stub environment before app.main is imported by the parent conftest."""
    stubs = {
        "REFRESH_TOKEN_PEPPER": "stub-pepper-for-tests",
        "MSG91_AUTH_KEY": "stub-msg91-key",
        "MSG91_TEMPLATE_ID": "stub-template-id",
        "RAZORPAY_KEY_ID": "stub-rzp-key",
        "RAZORPAY_KEY_SECRET": "stub-rzp-secret",
        "RAZORPAY_WEBHOOK_SECRET": "stub-webhook-secret",
        "GEMINI_API_KEY": "stub-gemini-key",
        "GCS_BUCKET": "stub-bucket",
        "GCS_PROJECT_ID": "stub-project",
        "LANGFUSE_PUBLIC_KEY": "stub-lf-public",
        "LANGFUSE_SECRET_KEY": "stub-lf-secret",
        "AUDIT_PII_SALT": "stub-pii-salt",
        "CORS_ALLOWED_ORIGINS": "http://localhost:4200",
        # Required by the parent conftest safety guard (must end in _test)
        "DATABASE_URL": "postgresql+asyncpg://meesell:password@localhost:5432/meesell_test",
        "APP_ENV": "development",
    }
    for k, v in stubs.items():
        os.environ.setdefault(k, v)
