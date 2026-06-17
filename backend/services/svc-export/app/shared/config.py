"""svc-export configuration — TRIMMED Pydantic Settings singleton.

Vendored from the monolith ``app.shared.config`` (BACKEND_ARCHITECTURE.md
§5.D) but TRIMMED to only the env vars the export service consumes per
spec §3.A:

* ``DATABASE_URL``  — async PostgreSQL DSN.  The export repository binds
  to the ``export`` Postgres schema (Sub-Plan A schema-split); the cross-
  schema ``public.audit_events`` write in ``tasks.py`` is fully-qualified.
* ``VALKEY_URL``    — DB-agnostic base URL.  Celery broker = DB 1, results
  = DB 2; the cosmetic export-format hint uses DB 0.
* ``JWT_SECRET`` / ``JWT_ALGORITHM`` — LOCAL JWT verification (A2: each
  service verifies the user JWT locally via the vendored ``core/auth.py``).
* ``GCS_*``         — XLSX + image-ZIP upload + signed-URL issuance.
* ``APP_ENV``       — environment discriminator.
* ``MONOLITH_INTERNAL_BASE_URL`` — base URL for the 4 HTTP-shim clients.
  During Sub-Plan A the callees (catalog / category / customer / image)
  are STILL IN-PROCESS in the monolith (R4 hybrid posture), so the shim
  points at the monolith ClusterIP (default ``http://monolith-svc:8001``).

EXPLICITLY ABSENT (the monolith Settings declares these; svc-export does
NOT — export is deterministic per §14.A and uses no SMS/payment):
* GEMINI_API_KEY / GEMINI_MODEL
* LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST
* MSG91_AUTH_KEY / MSG91_TEMPLATE_ID
* RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET / RAZORPAY_WEBHOOK_SECRET
* AI_DAILY_BUDGET_INR / AI_BUDGET_ALARM_THRESHOLD
* REFRESH_TOKEN_PEPPER* (export issues no tokens — verify only)

Pool sizing
-----------
svc-export is WORKER-HEAVY (the Celery export pipeline does the work; the
API surface is a thin initiate + poll).  The API-tier pool is therefore
SMALL — ``DB_POOL_SIZE=3`` / ``DB_MAX_OVERFLOW=2`` (vs the monolith's
10/5).  The Celery worker uses NullPool via ``make_worker_session`` so the
pool size does not bound worker concurrency.
"""

from __future__ import annotations

import sys
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# ── Required-field registry ────────────────────────────────────────────────
# The validator at the bottom SystemExits at boot if any of these are empty.
REQUIRED_FIELDS: tuple[str, ...] = (
    # Database
    "DATABASE_URL",
    # Valkey
    "VALKEY_URL",
    # JWT / Auth (local verification)
    "JWT_SECRET",
    # GCS
    "GCS_BUCKET",
    "GCS_PROJECT_ID",
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
    """svc-export trimmed application settings — single Pydantic Settings singleton.

    Only the export-relevant env vars are declared.  Model config is locked.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Database ───────────────────────────────────────────────────────────
    # The repository binds to the ``export`` Postgres schema (Sub-Plan A).
    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 3  # SMALL — worker-heavy service (spec §3.A)
    DB_MAX_OVERFLOW: int = 2
    DB_POOL_RECYCLE: int = 1800  # 30 min
    DB_ECHO: bool = False

    # ── Valkey ─────────────────────────────────────────────────────────────
    # DB number selected by the factories in shared.valkey / celery_app, NOT
    # by the URL.
    VALKEY_URL: str = ""

    # ── JWT / Auth (LOCAL verification — A2) ───────────────────────────────
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_SECONDS: int = 900

    # ── GCS ────────────────────────────────────────────────────────────────
    GCS_BUCKET: str = ""
    GCS_PROJECT_ID: str = ""
    GCS_SIGNED_URL_TTL_SECONDS: int = 3600  # 1 h per MVP_ARCH §10.8

    # ── Audit (PII scrubber salt) ──────────────────────────────────────────
    AUDIT_PII_SALT: str = ""

    # ── Rate limits ────────────────────────────────────────────────────────
    RL_PER_IP_PER_MINUTE: int = 120

    # ── Monolith internal base URL (R4 hybrid — HTTP shim target) ──────────
    # The 4 extracted_clients shims forward to the monolith's /internal/*
    # contract during Sub-Plan A (callees still in-process in the monolith).
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
                f"(see svc-export shared/config.py REQUIRED_FIELDS)"
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
