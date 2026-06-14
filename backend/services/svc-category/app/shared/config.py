"""svc-category configuration — TRIMMED Pydantic Settings singleton.

Vendored from the monolith ``app.shared.config`` (BACKEND_ARCHITECTURE.md
§5.D) but TRIMMED to only the env vars the category service consumes
(Sub-Plan F §Code-surfaces ``shared/config``):

* ``DATABASE_URL``  — async PostgreSQL DSN.  The repository binds to the
  ``category`` Postgres schema (Sub-Plan F schema-split ``c4f1e7a9d302``);
  the cross-schema ``public.audit_events`` write in the vendored
  ``ai_ops.cost_tracker`` is fully-qualified by the ORM model binding.
* ``VALKEY_URL``    — DB-agnostic base URL.  DB 0 = OTP/rate-limit + the
  SHARED ai_ops budget brake (un-prefixed keyspace); DB 3 = the read-through
  cache (``category:``-prefixed keys — the heaviest cache consumer, §6.7).
* ``JWT_SECRET`` / ``JWT_ALGORITHM`` / ``ACCESS_TOKEN_TTL_SECONDS`` — LOCAL
  JWT verification (D7/A2: each service verifies the user JWT locally via the
  vendored ``core/auth.py``; iam-svc is NEVER consulted per-request).  The
  ``REFRESH_TOKEN_PEPPER*`` fields are vendored with defaults because
  ``core/auth.py`` references them, but category issues/rotates NO tokens
  (verify-only) so they are NOT in ``REQUIRED_FIELDS``.
* ``GEMINI_*`` / ``LANGFUSE_*`` / ``AI_DAILY_BUDGET_INR`` /
  ``AI_BUDGET_ALARM_THRESHOLD`` — the VENDORED ai_ops smart_picker.v1 step
  (F1/D6).  GEMINI_API_KEY is required; LANGFUSE_* degrade to a no-op when
  unset (the adapter never raises — §6.F).
* ``AUDIT_PII_SALT`` — used by the vendored audit_mw PII scrubber.
* ``CACHE_VERSION`` — read-through cache version prefix (§4.D / §6.4); bumps
  on the quarterly Meesho corpus refresh.
* ``RL_PER_IP_PER_MINUTE`` — vendored rate_limit_mw per-IP DDoS floor.
* ``FEATURE_SMART_PICKER_ENABLED`` — the ``/categories/suggest`` 404 flag
  guard (router.py).  RETAINED in the trim — a vendored route that reads a
  trimmed-away flag is the MS-D flag-parity reject-class defect.
* ``APP_ENV``       — environment discriminator.

EXPLICITLY ABSENT (the monolith Settings declares these; svc-category does
NOT — category has no SMS/payment/storage/worker surface):
* MSG91_AUTH_KEY / MSG91_TEMPLATE_ID
* RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET / RAZORPAY_WEBHOOK_SECRET
* GCS_BUCKET / GCS_PROJECT_ID / GCS_SIGNED_URL_TTL_SECONDS (no storage)
* MONOLITH_INTERNAL_BASE_URL (category has ZERO outbound domain calls — it is
  a pure callee; no HTTP shim client)
* openpyxl / celery vars (no XLSX, no worker)

Budget brake (SHARED, NOT namespaced — F3.c / D6)
-------------------------------------------------
The vendored ``app.ai_ops.budget_cap`` Valkey keys (``ai:cost:daily:{date}``,
``ai:cost:pending:{date}``, ``ai:budget:reservation:{id}``,
``ai:cost:user:{user_id}:hourly:{hr}``) are UN-prefixed and live on Valkey
DB 0 — the global ₹500/day cap is SHARED across all services (monolith +
svc-category + every other AI-consuming service).  Do NOT namespace them.
Only category's OWN read-through cache keys (DB 3) get the ``category:``
prefix — applied in ``shared/valkey.py``'s cache factory, NOT here.
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
    # AI ops (smart_picker.v1 vendored step)
    "GEMINI_API_KEY",
    # Audit (PII scrubber salt — used by the vendored audit_mw)
    "AUDIT_PII_SALT",
    # CORS
    "CORS_ALLOWED_ORIGINS",
    # App
    "APP_ENV",
)


class Settings(BaseSettings):
    """svc-category trimmed application settings — single Pydantic Settings singleton."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Database ───────────────────────────────────────────────────────────
    # The repository binds to the ``category`` Postgres schema (Sub-Plan F).
    # Read-heavy + cache-fronted → modest pool.
    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_RECYCLE: int = 1800  # 30 min
    DB_ECHO: bool = False

    # ── Valkey ─────────────────────────────────────────────────────────────
    # DB number selected by the factories in shared.valkey, NOT by the URL.
    # ai_ops budget brake uses DB 0 (SHARED, un-prefixed); cache uses DB 3
    # (``category:``-prefixed).
    VALKEY_URL: str = ""

    # ── JWT / Auth (LOCAL verification — D7/A2) ────────────────────────────
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_SECONDS: int = 900
    # Vendored core/auth.py references the refresh-token pepper fields; category
    # issues/rotates NO tokens (verify-only) so they default + stay non-required.
    REFRESH_TOKEN_TTL_SECONDS: int = 604800
    REFRESH_TOKEN_PEPPER: str = ""
    REFRESH_TOKEN_PEPPER_PREVIOUS: str = ""
    REFRESH_TOKEN_PEPPER_VERSION: int = 1

    # ── AI ops (VENDORED smart_picker.v1 step — F1/D6) ─────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    # LangFuse degrades to no-op when unset (adapter never raises — §6.F).
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    # SHARED ₹500/day global cap — keyspace is un-prefixed (DB 0) per F3.c/D6.
    AI_DAILY_BUDGET_INR: int = 500
    AI_BUDGET_ALARM_THRESHOLD: float = 0.80  # 80% alarm before hard-stop

    # ── Audit (PII scrubber salt) ──────────────────────────────────────────
    AUDIT_PII_SALT: str = ""

    # ── Cache (read-through, DB 3) ─────────────────────────────────────────
    CACHE_VERSION: str = "v1"  # bumps on quarterly Meesho corpus refresh

    # ── Rate limits ────────────────────────────────────────────────────────
    RL_PER_IP_PER_MINUTE: int = 120

    # ── CORS ───────────────────────────────────────────────────────────────
    CORS_ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = Field(default_factory=list)
    CORS_ALLOW_CREDENTIALS: bool = True

    # ── App ────────────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"

    # ── Feature flags ──────────────────────────────────────────────────────
    # /categories/suggest 404-guards on this (router.py).  RETAINED in the trim
    # — dropping a flag a vendored route reads is the MS-D flag-parity defect.
    FEATURE_SMART_PICKER_ENABLED: bool = True

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
                f"(see svc-category shared/config.py REQUIRED_FIELDS)"
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
