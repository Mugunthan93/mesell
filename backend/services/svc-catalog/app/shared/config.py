"""svc-catalog configuration — TRIMMED Pydantic Settings singleton.

Vendored from the monolith ``app.shared.config`` (BACKEND_ARCHITECTURE.md §5.D)
but TRIMMED to the env vars the catalog service consumes (SUB_PLAN_0H §code-surfaces).

THE TRIM IS NOT FREE (MS-D flag-parity lesson)
----------------------------------------------
Every ``settings.<X>`` read by ANY vendored file (service, router, middleware,
ai_ops, adapters, extracted_clients) MUST survive the trim — a vendored route/mw
referencing a trimmed-away config field 500s EVERY request with an
Attribute. The 3 FEATURE flags below back the §10 mount guard + 2 route 404
guards and are LOAD-BEARING — dropping any is the MS-D reject class.

Catalog-specific surface (vs the deterministic-pricing trim):
* ``DATABASE_URL``  — async PostgreSQL DSN.  catalog OWNS the ``catalog`` schema
  (catalogs/products/product_drafts moved public→catalog in MS-H Phase A,
  migration ``a8f3b2e9c1d5``).  LARGEST POOL (autosave write-heavy — §2.E line
  207 "catalog gets the largest pool").
* ``VALKEY_URL``    — DB 0 (rate-limit windows + audit-coalesce + plan_guard
  product_count COUNT path + the SHARED ai:* budget brake — H3.c).  catalog is
  NOT a DB-3 cache consumer (fetch_schema caching lives in category-svc).
* ``JWT_SECRET`` / ``JWT_ALGORITHM`` — LOCAL JWT verification (A2 / D7).
* ``GEMINI_*`` / ``LANGFUSE_*`` / ``AI_DAILY_BUDGET_INR`` /
  ``AI_BUDGET_ALARM_THRESHOLD`` — the VENDORED ai_ops ``autofill.v1`` path.
* ``CATEGORY_SVC_BASE_URL`` / ``CUSTOMER_SVC_BASE_URL`` — the 5 OUTBOUND shims
  target REAL sibling pods (NOT the monolith — catalog runs at MS-5, §H5).
* ``AUDIT_PII_SALT`` — the vendored audit_mw PII scrubber.
* ``CACHE_VERSION`` — retained for parity (core/cache versioned-key contract).
* the 3 FEATURE flags — the §10 mount guard + 2 route 404 guards.
* ``APP_ENV``       — environment discriminator.

EXPLICITLY ABSENT (the monolith Settings declares these; svc-catalog does NOT):
* MSG91_AUTH_KEY / MSG91_TEMPLATE_ID            (no SMS surface)
* RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET / *     (no payment surface)
* GCS_BUCKET / GCS_PROJECT_ID / GCS_SIGNED_*    (no storage surface — autofill
  is TEXT not vision; image_refs is the dead-branch empty tuple)
* REFRESH_TOKEN_PEPPER*                         (catalog issues no tokens)
* MONOLITH_INTERNAL_BASE_URL                    (callees are REAL pods, not the
  monolith — replaced by the 2 per-callee base URLs)
* NO celery / broker / result DB                (catalog has NO worker)
"""

from __future__ import annotations

import sys
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# ── Required-field registry ────────────────────────────────────────────────
# The validator at the bottom SystemExits at boot if any of these are empty.
REQUIRED_FIELDS: tuple[str, ...] = (
    # Database (owns the catalog schema + auth existence check + audit wiring)
    "DATABASE_URL",
    # Valkey
    "VALKEY_URL",
    # JWT / Auth (local verification)
    "JWT_SECRET",
    # AI (vendored ai_ops autofill.v1 path)
    "GEMINI_API_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    # Audit (PII scrubber salt — used by the vendored audit_mw + cost_tracker)
    "AUDIT_PII_SALT",
    # CORS
    "CORS_ALLOWED_ORIGINS",
    # Outbound shim targets (REAL sibling pods — §H5)
    "CATEGORY_SVC_BASE_URL",
    "CUSTOMER_SVC_BASE_URL",
    # App
    "APP_ENV",
)


class Settings(BaseSettings):
    """svc-catalog trimmed application settings — single Pydantic Settings singleton."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Database ───────────────────────────────────────────────────────────
    # catalog OWNS the ``catalog`` schema.  LARGEST POOL (autosave write-heavy —
    # §2.E line 207).  The 3 catalog ORM models bind ``{"schema": "catalog"}``.
    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 10  # largest pool — autosave write-heavy (§2.E line 207)
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_RECYCLE: int = 1800  # 30 min
    DB_ECHO: bool = False

    # ── Valkey ─────────────────────────────────────────────────────────────
    # DB number selected by the factory in shared.valkey, NOT by the URL.
    # catalog uses DB 0 (rate-limit + audit-coalesce + plan_guard COUNT + the
    # SHARED ai:* budget brake — H3.c).  It is NOT a DB-3 cache consumer.
    VALKEY_URL: str = ""

    # ── JWT / Auth (LOCAL verification — A2 / D7) ──────────────────────────
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_SECONDS: int = 900

    # ── AI Ops (vendored autofill.v1 path) ─────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    # The ₹500 daily cap is SHARED/GLOBAL across category+catalog+image via the
    # un-prefixed ``ai:*`` Valkey keyspace (H3.c R4) — this value is the per-day
    # numerator the SHARED brake serialises against.
    AI_DAILY_BUDGET_INR: int = 500
    AI_BUDGET_ALARM_THRESHOLD: float = 0.80

    # ── Audit (PII scrubber salt) ──────────────────────────────────────────
    AUDIT_PII_SALT: str = ""

    # ── Cache (versioned-key contract parity) ──────────────────────────────
    CACHE_VERSION: str = "v1"

    # ── Rate limits ────────────────────────────────────────────────────────
    RL_PER_IP_PER_MINUTE: int = 120

    # ── Outbound shim targets (REAL sibling pods — §H5) ────────────────────
    # catalog runs at MS-5 — BOTH callees are already extracted pods.  These
    # point at the sibling ClusterIPs (NOT the monolith).
    CATEGORY_SVC_BASE_URL: str = "http://category-svc:8001"
    CUSTOMER_SVC_BASE_URL: str = "http://customer-svc:8001"

    # ── CORS ───────────────────────────────────────────────────────────────
    CORS_ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = Field(default_factory=list)
    CORS_ALLOW_CREDENTIALS: bool = True

    # ── App ────────────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"

    # ── Feature flags (LOAD-BEARING — the §10 mount guard + 2 route guards) ──
    # FEATURE_CATALOG_FORM_ENABLED: gates the ENTIRE catalog router mount in
    # main.py (row-26 / R9 — the route count is conditional).  Mirrors the
    # monolith definition at backend/app/shared/config.py:209.  When False the
    # /api/v1/products/* surface falls through to FastAPI's default 404.
    FEATURE_CATALOG_FORM_ENABLED: bool = True
    # FEATURE_AI_AUTOFILL_ENABLED: POST /products/{id}/autofill returns 404 when
    # False (router guard).  Mirrors backend/app/shared/config.py:216.
    FEATURE_AI_AUTOFILL_ENABLED: bool = True
    # FEATURE_LIVE_PREVIEW_ENABLED: dev default FALSE (the ONLY V1 flag defaulting
    # False — gated rollout).  GET /products/{id}/preview returns 404 / raises
    # MeesellError(code="feature.live_preview.disabled") when False.  Mirrors
    # backend/app/shared/config.py:237.
    FEATURE_LIVE_PREVIEW_ENABLED: bool = False

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
                f"(see svc-catalog shared/config.py REQUIRED_FIELDS)"
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
