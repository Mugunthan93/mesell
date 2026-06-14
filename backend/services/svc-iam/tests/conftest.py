"""svc-iam test fixtures — env bootstrap.

The trimmed ``Settings`` singleton loads at import time and ``SystemExit``s if
any ``REQUIRED_FIELD`` is empty (shared/config.py ``_require_non_empty``), so the
env MUST be populated BEFORE any ``app.*`` import.  This conftest sets
dummy-but-well-formed values for every required field at collection time.

iam is all-✗ in the call matrix (SUB_PLAN_0G §0.4) — there is NO
``extracted_clients`` transport to reset (unlike pricing / dashboard).  The
heavy hybrid-mode integration test (``test_iam_extraction.py`` — FE-D5 cookie /
allowlist round-trip, cross-schema audit, local-JWT cross-service validation) is
LEAD-owned (meesell-backend-coordinator, Phase C) and lands AFTER the
auth-builder freezes ``service.py`` + ``core/auth.py`` on this branch.  This
conftest only bootstraps the env so the services-builder scaffolding smoke test
(``test_scaffolding.py``) can import the vendored modules.
"""

from __future__ import annotations

import os

# ── Dummy env — populated before any ``app.*`` import ───────────────────────
# DATABASE_URL points at the local Homebrew PG 16 `meesell` db by default so a
# future PG-gated cross-schema audit round-trip can run locally; CI overrides it.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://mugunthansrinivasan@localhost:5432/meesell",
)
os.environ.setdefault("VALKEY_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-svc-iam")
os.environ.setdefault("REFRESH_TOKEN_PEPPER", "test-refresh-pepper-svc-iam")
os.environ.setdefault("MSG91_AUTH_KEY", "test-msg91-auth-key")
os.environ.setdefault("MSG91_TEMPLATE_ID", "test-msg91-template-id")
os.environ.setdefault("RAZORPAY_KEY_ID", "test-razorpay-key-id")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "test-razorpay-key-secret")
os.environ.setdefault("RAZORPAY_WEBHOOK_SECRET", "test-razorpay-webhook-secret")
os.environ.setdefault("AUDIT_PII_SALT", "test-audit-pii-salt")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "https://app.mesell.xyz")
os.environ.setdefault("APP_ENV", "development")
