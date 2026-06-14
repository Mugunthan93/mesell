"""svc-category test bootstrap — inject the trimmed-config env BEFORE app import.

The ``app.shared.config.settings`` singleton loads at import time and
SystemExits if any ``REQUIRED_FIELDS`` is empty.  Set CI-safe placeholders via
``os.environ.setdefault`` here (conftest is imported before any test module),
so ``import app.main`` / ``import app.service`` succeed without a live env.

These values are import-smoke placeholders only — no test in the services-builder
invariant suite touches a live DB / Valkey (those are Phase-C, PG-gated).
"""

from __future__ import annotations

import os

_DUMMY_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://category_user:x@localhost:5432/meesell",
    "VALKEY_URL": "redis://localhost:6379",
    "JWT_SECRET": "test-jwt-secret-not-a-real-secret",
    "GEMINI_API_KEY": "test-gemini-key",
    "AUDIT_PII_SALT": "test-audit-salt",
    "CORS_ALLOWED_ORIGINS": "https://app.meesell.dev",
    "APP_ENV": "development",
}

for _k, _v in _DUMMY_ENV.items():
    os.environ.setdefault(_k, _v)
