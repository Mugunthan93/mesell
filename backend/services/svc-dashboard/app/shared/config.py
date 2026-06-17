"""svc-dashboard configuration — TRIMMED Pydantic Settings singleton.

Vendored from the monolith ``app.shared.config`` (BACKEND_ARCHITECTURE.md
§5.D) but TRIMMED to only the env vars the dashboard service consumes per
spec §3.A:

* ``DATABASE_URL``  — async PostgreSQL DSN.  dashboard owns NO schema (§13.D);
  the DSN is used ONLY for the vendored ``core/auth.get_current_user``
  existence check (``db.get(User, sub)``) + the ``audit_mw`` /
  ``get_db`` wiring.  The pool is therefore TINY.
* ``VALKEY_URL``    — DB-agnostic base URL.  DB 0 carries the per-IP /
  per-route rate-limit sliding windows + the audit-coalesce markers.
* ``JWT_SECRET`` / ``JWT_ALGORITHM`` — LOCAL JWT verification (A2 / D7: each
  service verifies the user JWT locally via the vendored ``core/auth.py``).
* ``FEATURE_TRACKING_DASHBOARD_ENABLED`` — the 404 feature-flag guard the
  router enforces BEFORE the service call (router.py source).
* ``MONOLITH_INTERNAL_BASE_URL`` — base URL for the 2 HTTP-shim clients
  (catalog + customer).  During MS-2 the callees (catalog / customer) are
  STILL IN-PROCESS in the monolith (R4 hybrid posture), so the shim points at
  the monolith ClusterIP (default ``http://monolith-svc:8001``).
* ``APP_ENV``       — environment discriminator.

EXPLICITLY ABSENT (the monolith Settings declares these; svc-dashboard does
NOT — dashboard is a pure read with no AI / SMS / payment / storage):
* GEMINI_API_KEY / GEMINI_MODEL
* LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST
* MSG91_AUTH_KEY / MSG91_TEMPLATE_ID
* RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET / RAZORPAY_WEBHOOK_SECRET
* GCS_BUCKET / GCS_PROJECT_ID / GCS_SIGNED_URL_TTL_SECONDS
* AI_DAILY_BUDGET_INR / AI_BUDGET_ALARM_THRESHOLD
* REFRESH_TOKEN_PEPPER* (dashboard issues no tokens — verify only)

Pool sizing
-----------
svc-dashboard does NO direct data access (catalog + customer HTTP shims do
the work; the API surface is a thin compose).  The API-tier pool is therefore
the SMALLEST of any service — ``DB_POOL_SIZE=2`` / ``DB_MAX_OVERFLOW=1`` (the
pool exists only for the auth existence check + audit write).
"""

from __future__ import annotations

import sys
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# ── Required-field registry ────────────────────────────────────────────────
# The validator at the bottom SystemExits at boot if any of these are empty.
REQUIRED_FIELDS: tuple[str, ...] = (
    # Database (auth existence check + audit wiring only — no owned schema)
    "DATABASE_URL",
    # Valkey
    "VALKEY_URL",
    # JWT / Auth (local verification)
    "JWT_SECRET",
    # Audit (PII scrubber salt — used by the vendored audit_mw)
    "AUDIT_PII_SALT",
    # CORS
    "CORS_ALLOWED_ORIGINS",
    # Monolith shim base URL (R4 hybrid posture)
    "MONOLITH_INTERNAL_BASE_URL",
    # App
    "APP_ENV",
)


class Settings(BaseSettings):
    """svc-dashboard trimmed application settings — single Pydantic Settings singleton.

    Only the dashboard-relevant env vars are declared.  Model config is locked.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Database ───────────────────────────────────────────────────────────
    # dashboard owns NO schema (§13.D); the DSN backs only the auth existence
    # check + audit wiring.  TINY pool — dashboard delegates all data access
    # to its catalog + customer HTTP shims.
    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 2  # SMALLEST — no owned data access (spec §3.A)
    DB_MAX_OVERFLOW: int = 1
    DB_POOL_RECYCLE: int = 1800  # 30 min
    DB_ECHO: bool = False

    # ── Valkey ─────────────────────────────────────────────────────────────
    # DB number selected by the factories in shared.valkey, NOT by the URL.
    VALKEY_URL: str = ""

    # ── JWT / Auth (LOCAL verification — A2 / D7) ──────────────────────────
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_SECONDS: int = 900

    # ── Feature flag (router 404 guard — spec §3.B) ────────────────────────
    # The dashboard router returns 404 when this is False, BEFORE the service
    # call.  Carried in Settings so the extracted guard fires identically.
    FEATURE_TRACKING_DASHBOARD_ENABLED: bool = True

    # ── Audit (PII scrubber salt) ──────────────────────────────────────────
    AUDIT_PII_SALT: str = ""

    # ── Rate limits ────────────────────────────────────────────────────────
    RL_PER_IP_PER_MINUTE: int = 120

    # ── Monolith internal base URL (R4 hybrid — HTTP shim target) ──────────
    # The 2 extracted_clients shims (catalog + customer) forward to the
    # monolith's /internal/* contract during MS-2 (callees still in-process).
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
                f"(see svc-dashboard shared/config.py REQUIRED_FIELDS)"
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
