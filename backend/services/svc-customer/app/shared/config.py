"""svc-customer configuration — TRIMMED Pydantic Settings singleton.

Vendored from the monolith ``app.shared.config`` (BACKEND_ARCHITECTURE.md
§5.D) but TRIMMED to only the env vars the customer service consumes per spec
§3.A:

* ``DATABASE_URL``  — async PostgreSQL DSN.  customer OWNS the ``customer``
  schema (``customer.seller_profile`` — moved by migration ``a9f3b2c5e1d8``);
  the DSN backs the repository's 4 ``scope_to_user`` CRUD methods, the
  vendored ``core/auth.get_current_user`` existence check (``db.get(User,
  sub)`` against ``public.users``), and the ``audit_mw`` cross-schema write to
  ``public.audit_events``.
* ``VALKEY_URL``    — DB-agnostic base URL.  DB 0 carries the per-IP /
  per-route rate-limit sliding windows + audit-coalesce markers; DB 3 carries
  the read-through cache (required_fields 60 s / super_category_set 3600 s).
* ``JWT_SECRET`` / ``JWT_ALGORITHM`` — LOCAL JWT verification (A2 / D7: each
  service verifies the user JWT locally via the vendored ``core/auth.py``).
* ``CACHE_VERSION`` — the ``meesell:v{cv}:`` prefix on every cache key (§4.D).
* ``AUDIT_PII_SALT`` — used by the vendored ``audit_mw`` PII scrubber.
* ``MONOLITH_INTERNAL_BASE_URL`` — base URL for the OUTBOUND category shim
  (``GET /internal/super-categories``).  During MS-3 the callee (category) is
  STILL IN-PROCESS in the monolith (R4 hybrid posture), so the shim points at
  the monolith ClusterIP (default ``http://monolith-svc:8001``); it re-points
  to category-svc at MS-4 via infra config — NO code change.
* ``APP_ENV``       — environment discriminator.

EXPLICITLY ABSENT (the monolith Settings declares these; svc-customer does NOT
— customer is profile CRUD with no AI / SMS / payment / storage / Celery):
* GEMINI_API_KEY / GEMINI_MODEL
* LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST
* MSG91_AUTH_KEY / MSG91_TEMPLATE_ID
* RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET / RAZORPAY_WEBHOOK_SECRET
* GCS_BUCKET / GCS_PROJECT_ID / GCS_SIGNED_URL_TTL_SECONDS
* AI_DAILY_BUDGET_INR / AI_BUDGET_ALARM_THRESHOLD
* REFRESH_TOKEN_PEPPER* (customer issues no tokens — verify only)
* Celery broker (DB 1) / result-backend (DB 2) URLs
"""

from __future__ import annotations

import sys
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# ── Required-field registry ────────────────────────────────────────────────
# The validator at the bottom SystemExits at boot if any of these are empty.
REQUIRED_FIELDS: tuple[str, ...] = (
    # Database (customer owns the `customer` schema)
    "DATABASE_URL",
    # Valkey (DB 0 rate-limit/audit-coalesce + DB 3 read-through cache)
    "VALKEY_URL",
    # JWT / Auth (local verification)
    "JWT_SECRET",
    # Audit (PII scrubber salt — used by the vendored audit_mw)
    "AUDIT_PII_SALT",
    # CORS
    "CORS_ALLOWED_ORIGINS",
    # Monolith shim base URL (R4 hybrid posture — outbound category shim)
    "MONOLITH_INTERNAL_BASE_URL",
    # App
    "APP_ENV",
)


class Settings(BaseSettings):
    """svc-customer trimmed application settings — single Pydantic Settings singleton."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Database ───────────────────────────────────────────────────────────
    # customer owns the `customer` schema (customer.seller_profile).  The pool
    # is small — one table, query-light onboarding wizard traffic.
    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 2
    DB_POOL_RECYCLE: int = 1800  # 30 min
    DB_ECHO: bool = False

    # ── Valkey ─────────────────────────────────────────────────────────────
    # DB number selected by the factories in shared.valkey, NOT by the URL.
    # DB 0 = rate-limit / audit-coalesce; DB 3 = read-through cache.
    VALKEY_URL: str = ""

    # ── JWT / Auth (LOCAL verification — A2 / D7) ──────────────────────────
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_SECONDS: int = 900

    # ── Cache (read-through versioning — §4.D) ─────────────────────────────
    # The `meesell:v{cv}:` prefix on every cache key.  Bumps on the quarterly
    # Meesho corpus refresh to invalidate super_category_set atomically.
    CACHE_VERSION: str = "v1"

    # ── Audit (PII scrubber salt) ──────────────────────────────────────────
    AUDIT_PII_SALT: str = ""

    # ── Rate limits ────────────────────────────────────────────────────────
    RL_PER_IP_PER_MINUTE: int = 120

    # ── Monolith internal base URL (R4 hybrid — OUTBOUND category shim) ────
    # The category_client outbound shim (GET /internal/super-categories)
    # forwards to the monolith's /internal/* contract during MS-3 (category
    # still in-process); re-points to category-svc at MS-4 via infra config.
    MONOLITH_INTERNAL_BASE_URL: str = "http://monolith-svc:8001"

    # ── CORS ───────────────────────────────────────────────────────────────
    CORS_ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = Field(default_factory=list)
    CORS_ALLOW_CREDENTIALS: bool = True

    # ── App ────────────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"

    # ── Validators ─────────────────────────────────────────────────────────
    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: object) -> object:
        """Accept comma-separated string OR JSON list OR Python list."""
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                import json

                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    return stripped
                return parsed
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return v

    @model_validator(mode="after")
    def _forbid_cors_wildcard(self) -> "Settings":
        """CORS with credentials forbids the ``*`` origin (§4.G amendment)."""
        if "*" in self.CORS_ALLOWED_ORIGINS:
            raise SystemExit(
                "FATAL: CORS_ALLOWED_ORIGINS may not contain '*' "
                "(CORS with credentials forbids wildcard — §4.G amendment)"
            )
        return self

    @model_validator(mode="after")
    def _require_non_empty(self) -> "Settings":
        """Fail-fast: every required field must be non-empty."""
        missing: list[str] = []
        for fname in REQUIRED_FIELDS:
            value = getattr(self, fname, None)
            if value is None or value == "" or value == []:
                missing.append(fname)
        if missing:
            joined = ", ".join(missing)
            raise SystemExit(
                f"FATAL: required env var(s) empty or unset: {joined} "
                f"(see svc-customer shared/config.py REQUIRED_FIELDS)"
            )
        return self

    # ── Convenience properties ──────────────────────────────────────────────
    @property
    def is_dev(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_staging(self) -> bool:
        return self.APP_ENV == "staging"

    @property
    def is_prod(self) -> bool:
        return self.APP_ENV == "production"


def _load_settings() -> Settings:
    """Load Settings — SystemExit bubbles to the process."""
    try:
        return Settings()
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover — defensive boot trap
        print(f"FATAL: Settings load failed — {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


settings: Settings = _load_settings()
"""Module-level singleton — every other module imports this.

Locked rule: ``from app.shared.config import settings`` is the only valid
access path; NO module instantiates ``Settings()`` again.
"""
