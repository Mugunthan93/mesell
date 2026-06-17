"""svc-export test fixtures — env bootstrap + shim context reset.

The trimmed ``Settings`` singleton loads at import time and SystemExits if any
REQUIRED_FIELD is empty, so the env MUST be populated BEFORE ``app`` is
imported.  This conftest sets dummy-but-well-formed values for every required
field at collection time (the values are never used to reach a live service —
the shim tests mock the httpx transport).
"""

from __future__ import annotations

import os

# ── Dummy env — populated before any ``app.*`` import ───────────────────────
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://svc_export:svc_export@localhost:5432/meesell_test"
)
os.environ.setdefault("VALKEY_URL", "redis://localhost:6379")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-svc-export")
os.environ.setdefault("GCS_BUCKET", "meesell-test-bucket")
os.environ.setdefault("GCS_PROJECT_ID", "meesell-test-project")
os.environ.setdefault("AUDIT_PII_SALT", "test-audit-pii-salt")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "https://app.meesell.test")
os.environ.setdefault("MONOLITH_INTERNAL_BASE_URL", "http://monolith-svc:8001")
os.environ.setdefault("APP_ENV", "development")

import pytest  # noqa: E402

from app.core.extracted_clients import _transport  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_shim_context():
    """Reset the extracted_clients propagation context-vars around each test."""
    _transport.set_request_context(bearer_token=None, request_id=None)
    yield
    _transport.set_request_context(bearer_token=None, request_id=None)
