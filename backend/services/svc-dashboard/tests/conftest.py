"""svc-dashboard test fixtures — env bootstrap + shim context reset.

The trimmed ``Settings`` singleton (``app.shared.config``) loads at import time
and ``SystemExit``s if any ``REQUIRED_FIELDS`` entry is empty, so the env MUST
be populated BEFORE any ``app.*`` import.  This conftest sets dummy-but-well-
formed values for every required field at collection time (the values are never
used to reach a live service — the shim tests mock the httpx transport, and the
flag-guard test patches ``settings`` in place).

Mirrors ``svc-export/tests/conftest.py`` (SP01) with the dashboard-specific
required-field set: dashboard has NO GCS / AI / SMS / payment vars (it is a
pure read), so only the §config.REQUIRED_FIELDS tuple is populated.
"""

from __future__ import annotations

import os

# ── Dummy env — populated before any ``app.*`` import (config SystemExits on
#    an empty REQUIRED_FIELD at import time). ─────────────────────────────────
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://svc_dashboard:svc_dashboard@localhost:5432/meesell_test",
)
os.environ.setdefault("VALKEY_URL", "redis://localhost:6379")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-svc-dashboard")
os.environ.setdefault("AUDIT_PII_SALT", "test-audit-pii-salt")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "https://app.meesell.test")
os.environ.setdefault("MONOLITH_INTERNAL_BASE_URL", "http://monolith-svc:8001")
os.environ.setdefault("APP_ENV", "development")

import pytest  # noqa: E402

from app.core.extracted_clients import _transport  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_shim_context():
    """Reset the extracted_clients propagation context-vars around each test so
    a JWT/request-id set by one test never leaks into the next."""
    _transport.set_request_context(bearer_token=None, request_id=None)
    yield
    _transport.set_request_context(bearer_token=None, request_id=None)
