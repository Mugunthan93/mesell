"""svc-iam configuration — TRIMMED Pydantic Settings singleton.

Vendored from the monolith ``app.shared.config`` (BACKEND_ARCHITECTURE.md
§5.D) but TRIMMED to only the env vars the iam service consumes per
SUB_PLAN_0G §"Code surfaces" + spec_msG §3.C:

* ``DATABASE_URL``  — async PostgreSQL DSN.  iam OWNS the ``iam`` schema (the
  ``users`` table moved ``public`` → ``iam`` in the MS-4 Phase A schema-split,
  migration ``b1c2d3e4f5a6``).  The DSN backs the ``users`` reads/writes
  (``repository.py``) + the vendored ``core/auth.get_current_user`` existence
  check (``db.get(User, sub)`` against ``iam.users``) + the ``audit_mw``
  cross-schema write to ``public.audit_events`` (§7.I direct-ORM audit path
  fires on iam's auth routes).
* ``VALKEY_URL``    — DB-agnostic base URL.  DB 0 carries the OTP records
  (``otp:{phone}``) + the FE-D5 refresh-allowlist (``cache:refresh:v{N}:{hmac}``)
  + the per-IP / per-route rate-limit sliding windows + the audit-coalesce
  markers.  iam is NOT a cache consumer (DB 3 unused); it runs NO Celery so
  the broker (DB 1) / result backend (DB 2) factories are NOT vendored.
* ``JWT_SECRET`` / ``JWT_ALGORITHM`` — HS256 token signing AND LOCAL
  verification.  iam is the ONLY service that ISSUES tokens (the issuance /
  rotation half of ``core/auth.py``); every other service verifies the same
  ``JWT_SECRET``-signed JWT locally (A2 / D7).
* ``ACCESS_TOKEN_TTL_SECONDS`` / ``REFRESH_TOKEN_TTL_SECONDS`` — the FE-D5 TTLs
  (access JWT lifetime + refresh cookie lifetime).
* ``REFRESH_TOKEN_PEPPER`` / ``REFRESH_TOKEN_PEPPER_PREVIOUS`` /
  ``REFRESH_TOKEN_PEPPER_VERSION`` — the FE-D5 dual-pepper allowlist HMAC
  keying (R5 / PR #66).  The allowlist key is
  ``cache:refresh:v{VERSION}:{hmac_sha256(token, PEPPER)}``; reads fall back
  to ``v{VERSION-1}`` with ``REFRESH_TOKEN_PEPPER_PREVIOUS``.
* ``MSG91_AUTH_KEY`` / ``MSG91_TEMPLATE_ID`` — the OTP-send adapter
  (``POST /auth/otp/send``).
* ``RAZORPAY_KEY_ID`` / ``RAZORPAY_KEY_SECRET`` / ``RAZORPAY_WEBHOOK_SECRET`` —
  the Razorpay webhook HMAC verification (``POST /webhooks/razorpay``).
* ``AUDIT_PII_SALT`` — the vendored ``audit_mw`` PII scrubber salt.
* ``APP_ENV`` — environment discriminator.

EXPLICITLY ABSENT (the monolith Settings declares these; svc-iam does NOT —
iam owns identity / OTP / token issuance only, no AI / storage — SUB_PLAN_0G
§"Code surfaces"):
* GEMINI_API_KEY / GEMINI_MODEL
* LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST
* GCS_BUCKET / GCS_PROJECT_ID / GCS_SIGNED_URL_TTL_SECONDS
* AI_DAILY_BUDGET_INR / AI_BUDGET_ALARM_THRESHOLD
* CACHE_VERSION (iam reads no application cache — DB 3 unused)
* MONOLITH_INTERNAL_BASE_URL (iam is all-✗ in the call matrix — §0.4: NO
  outbound HTTP shims, so there is no monolith ClusterIP to point at)

Pool sizing
-----------
svc-iam does a single-row read (find_user_by_phone / get_user_by_id) +
single-row upsert (upsert_user_on_login) per auth request, plus the
cross-schema audit INSERT.  The local pool is small — ``DB_POOL_SIZE=2`` /
``DB_MAX_OVERFLOW=2`` (the OTP / allowlist hot path is Valkey, not Postgres).
"""

from __future__ import annotations

import sys
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# ── Required-field registry ────────────────────────────────────────────────
# The validator at the bottom SystemExits at boot if any of these are empty.
# Mirrors the monolith REQUIRED_FIELDS subset relevant to iam (§5.D).
REQUIRED_FIELDS: tuple[str, ...] = (
    # Database (owns the iam schema + auth existence check + audit wiring)
    "DATABASE_URL",
    # Valkey
    "VALKEY_URL",
    # JWT / Auth (signing + local verification)
    "JWT_SECRET",
    # FE-D5 dual-pepper allowlist (iam issues + rotates refresh tokens)
    "REFRESH_TOKEN_PEPPER",
    # MSG91 (OTP send)
    "MSG91_AUTH_KEY",
    "MSG91_TEMPLATE_ID",
    # Razorpay (webhook HMAC verify)
    "RAZORPAY_KEY_ID",
    "RAZORPAY_KEY_SECRET",
    "RAZORPAY_WEBHOOK_SECRET",
    # Audit (PII scrubber salt — used by the vendored audit_mw)
    "AUDIT_PII_SALT",
    # CORS
    "CORS_ALLOWED_ORIGINS",
    # App
    "APP_ENV",
)


class Settings(BaseSettings):
    """svc-iam trimmed application settings — single Pydantic Settings singleton.

    Only the iam-relevant env vars are declared.  Model config is locked.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Database ───────────────────────────────────────────────────────────
    # iam OWNS the ``iam`` schema (users moved public→iam in MS-4 Phase A,
    # migration b1c2d3e4f5a6).  The DSN points at the svc-iam Postgres role;
    # the User ORM model binds ``{"schema": "iam"}`` explicitly.
    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 2  # small — OTP/allowlist hot path is Valkey, not PG
    DB_MAX_OVERFLOW: int = 2
    DB_POOL_RECYCLE: int = 1800  # 30 min
    DB_ECHO: bool = False

    # ── Valkey ─────────────────────────────────────────────────────────────
    # DB number selected by the factory in shared.valkey, NOT by the URL.
    # iam uses DB 0 ONLY (OTP records + FE-D5 refresh-allowlist + rate-limit
    # sliding windows + audit-coalesce).  It runs NO Celery (no DB 1 / DB 2)
    # and reads no application cache (no DB 3).
    VALKEY_URL: str = ""

    # ── JWT / Auth (HS256 sign + LOCAL verify — A2 / D7) ───────────────────
    # iam is the ONLY service that issues tokens; every other service verifies
    # the same JWT_SECRET locally via the vendored core/auth.py.
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_SECONDS: int = 900  # prod 15 min; staging 60; dev 30
    REFRESH_TOKEN_TTL_SECONDS: int = 604800  # prod 7d; staging 300; dev 120

    # ── FE-D5 dual-pepper refresh allowlist (R5 / PR #66) ──────────────────
    # Allowlist key = cache:refresh:v{VERSION}:{hmac_sha256(token, PEPPER)}.
    # Reads try v{VERSION} (current PEPPER) then fall back to v{VERSION-1}
    # (PEPPER_PREVIOUS) during the rotation grace window; writes ALWAYS use the
    # current VERSION.  Derivation + the Lua rotation live in the vendored
    # core/auth.py (auth-builder's file).
    REFRESH_TOKEN_PEPPER: str = ""  # Secret Manager ref `refresh-token-pepper`
    REFRESH_TOKEN_PEPPER_PREVIOUS: str = ""  # set ONLY during pepper rotation
    REFRESH_TOKEN_PEPPER_VERSION: int = 1

    # ── MSG91 (OTP send) ───────────────────────────────────────────────────
    MSG91_AUTH_KEY: str = ""
    MSG91_TEMPLATE_ID: str = ""

    # ── Razorpay (webhook HMAC verify) ─────────────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # ── Audit (PII scrubber salt) ──────────────────────────────────────────
    AUDIT_PII_SALT: str = ""

    # ── Google Sign-In (google-auth feature, 2026-06-18) ───────────────────
    # GOOGLE_OAUTH_CLIENT_ID is the OAuth Web client ID used as the `audience`
    # for ID-token verification.  Modelled as a list (comma-split, like
    # CORS_ALLOWED_ORIGINS) so a future Android/iOS native client ID can be
    # added as a second accepted audience WITHOUT a config migration (design
    # §D.2 / §I.5).  The client ID is public (not a secret) but kept in config
    # for provenance uniformity.  Required ONLY when the feature flag is on
    # (conditional validator below) so existing envs do not break at boot.
    GOOGLE_OAUTH_CLIENT_ID: Annotated[list[str], NoDecode] = Field(default_factory=list)
    # Per-env rollout gate.  When False the /auth/google/verify route is NOT
    # mounted (404), so the OpenAPI surface + §17 endpoint count are unchanged.
    FEATURE_GOOGLE_AUTH_ENABLED: bool = False

    # ── Rate limits ────────────────────────────────────────────────────────
    RL_PER_IP_PER_MINUTE: int = 120  # DDoS-class default; per-route overrides

    # ── CORS ───────────────────────────────────────────────────────────────
    CORS_ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = Field(default_factory=list)
    CORS_ALLOW_CREDENTIALS: bool = True

    # ── App ────────────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"

    # ── Validators ─────────────────────────────────────────────────────────
    @field_validator("CORS_ALLOWED_ORIGINS", "GOOGLE_OAUTH_CLIENT_ID", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: object) -> object:
        """Accept comma-separated string OR JSON list OR Python list.

        Shared by CORS_ALLOWED_ORIGINS and GOOGLE_OAUTH_CLIENT_ID (the latter
        is a list of accepted OAuth client-ID audiences, see config field doc).
        """
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
        """CORS with credentials forbids the ``*`` origin (§4.G amendment).

        FE-D5 sends the refresh cookie cross-origin with credentials, so the
        wildcard origin is structurally forbidden.
        """
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
                f"(see svc-iam shared/config.py REQUIRED_FIELDS)"
            )
        return self

    @model_validator(mode="after")
    def _require_google_client_id_when_enabled(self) -> "Settings":
        """google-auth: GOOGLE_OAUTH_CLIENT_ID is required ONLY when the flag is on.

        Conditional (not in REQUIRED_FIELDS) so existing envs that never enable
        the feature boot cleanly.  When the flag IS on, an empty audience would
        disable the single most important verification check (audience
        confusion defence, design §G) — so fail fast.
        """
        if self.FEATURE_GOOGLE_AUTH_ENABLED and not self.GOOGLE_OAUTH_CLIENT_ID:
            raise SystemExit(
                "FATAL: FEATURE_GOOGLE_AUTH_ENABLED is true but "
                "GOOGLE_OAUTH_CLIENT_ID is empty — the OAuth audience is "
                "mandatory for ID-token verification (design §G audience "
                "confusion defence)."
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
