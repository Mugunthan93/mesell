"""svc-pricing test fixtures — env bootstrap + shim context reset.

The trimmed ``Settings`` singleton loads at import time and ``SystemExit``s if
any ``REQUIRED_FIELD`` is empty (shared/config.py ``_require_non_empty``), so the
env MUST be populated BEFORE any ``app.*`` import.  This conftest sets
dummy-but-well-formed values for every required field at collection time.

The shim tests mock the httpx transport (no live callee), so DATABASE_URL /
VALKEY_URL never reach a live service for those.  The ONE PG-gated test
(``test_cross_schema_audit_insert_round_trip``) reads DATABASE_URL and only runs
if a real Postgres is connectable at it (auth-otp no-tunnel pattern) — to run
that gate locally, point DATABASE_URL at a reachable PG 16 with the ``pricing``
+ ``public`` schemas creatable by the connecting role.
"""

from __future__ import annotations

import os

# ── Dummy env — populated before any ``app.*`` import ───────────────────────
# DATABASE_URL points at the local Homebrew PG 16 `meesell` db by default so the
# PG-gated cross-schema audit round-trip can run locally; CI overrides it.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://mugunthansrinivasan@localhost:5432/meesell",
)
os.environ.setdefault("VALKEY_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-svc-pricing")
os.environ.setdefault("AUDIT_PII_SALT", "test-audit-pii-salt")
os.environ.setdefault("MONOLITH_INTERNAL_BASE_URL", "http://monolith-svc:8001")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "https://app.meesell.test")
os.environ.setdefault("APP_ENV", "development")

import pytest  # noqa: E402

from app.core.extracted_clients import _transport  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_shim_context():
    """Reset the extracted_clients propagation context-vars around each test."""
    _transport.set_request_context(bearer_token=None, request_id=None)
    yield
    _transport.set_request_context(bearer_token=None, request_id=None)
