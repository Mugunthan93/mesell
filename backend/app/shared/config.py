"""Application configuration — Pydantic Settings singleton.

Per BACKEND_ARCHITECTURE.md §5.D, this module owns the **single** Pydantic
Settings class for the application.  Every env var the V1 backend reads is
declared here, grouped by the 11 §5.D tables (Database / Valkey / JWT-Auth /
MSG91 / Razorpay / Gemini / GCS / LangFuse / AI-Ops / Cache / Audit /
Rate-limits / CORS / App — the App group is a single field, so the table
count tallied verbatim in §5.D is 11 logical groups + App).

Secret sourcing
---------------
* Dev: ``.env`` at the backend repo root.  ``case_sensitive=True`` matches the
  K3s injection convention (``JWT_SECRET=...``, not ``jwt_secret=...``).
  ``extra="ignore"`` permits per-environment ``TF_VAR_*``/``KUBE_*`` keys to
  coexist with the Settings schema without being rejected.
* Staging + prod: GCP Secret Manager values are injected as pod env vars via
  ``envFrom: secretRef:`` (per ``meesell-infra-builder`` memory).  The same
  ``os.environ`` lookup path applies, so the Settings class does not care
  which mechanism populated the values.

Fail-fast at boot
-----------------
The ``_require_non_empty`` validator runs after pydantic finishes parsing.
If any field marked ``Required`` in §5.D is empty or unset, the process exits
with ``SystemExit`` and a stderr message that names the missing variable.
A half-configured process is forbidden — better to crash at boot than to
serve 500s in production.

JWT lifetime fields
-------------------
``JWT_EXPIRY_DAYS`` was DEPRECATED per the FE-D5 + FE-D6 amendments
(2026-06-05) and REMOVED during the §7 (``iam``) construction dispatch
(2026-06-06).  The replacement fields are ``ACCESS_TOKEN_TTL_SECONDS``
(default 15 min) + ``REFRESH_TOKEN_TTL_SECONDS`` (default 7 days).  Any
remaining import-time references to ``settings.JWT_EXPIRY_DAYS`` will fail
fast at the legacy call site — by design.
"""

from __future__ import annotations

import sys
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# ── Required-field registry ────────────────────────────────────────────────
# Every field listed below is "Required: yes" in §5.D.  The validator at the
# bottom of this module SystemExits at boot if any of these are empty.
REQUIRED_FIELDS: tuple[str, ...] = (
    # Database
    "DATABASE_URL",
    # Valkey
    "VALKEY_URL",
    # JWT / Auth
    "JWT_SECRET",
    "REFRESH_TOKEN_PEPPER",
    # MSG91
    "MSG91_AUTH_KEY",
    "MSG91_TEMPLATE_ID",
    # Razorpay
    "RAZORPAY_KEY_ID",
    "RAZORPAY_KEY_SECRET",
    "RAZORPAY_WEBHOOK_SECRET",
    # Gemini
    "GEMINI_API_KEY",
    # GCS
    "GCS_BUCKET",
    "GCS_PROJECT_ID",
    # LangFuse
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    # Audit
    "AUDIT_PII_SALT",
    # CORS
    "CORS_ALLOWED_ORIGINS",
    # App
    "APP_ENV",
)


class Settings(BaseSettings):
    """V1 application settings — single Pydantic Settings singleton.

    All env vars declared per BACKEND_ARCHITECTURE.md §5.D.  The model
    config is locked; specialists do NOT amend it.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Database (§5.D table 1) ────────────────────────────────────────────
    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_RECYCLE: int = 1800  # 30 min — recycle stale conns proactively
    DB_ECHO: bool = False

    # ── Valkey (§5.D table 2) ──────────────────────────────────────────────
    # DB number is selected by the factories in shared.valkey, NOT by the URL.
    VALKEY_URL: str = ""

    # ── JWT / Auth (§5.D table 3, FE-D5 ratified) ──────────────────────────
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_SECONDS: int = 900  # prod 15 min; staging 60; dev 30
    REFRESH_TOKEN_TTL_SECONDS: int = 604800  # prod 7d; staging 300; dev 120
    REFRESH_TOKEN_PEPPER: str = ""  # Secret Manager ref `refresh-token-pepper`

    # ── Dual-pepper grace-window rotation (R5, dual-pepper-rotation feature) ──
    # Optional — populated ONLY during the §2 (auth-secret-rotation runbook)
    # grace window.  Empty ("") == normal single-pepper mode: the dual-read
    # fallback in core.auth.validate_refresh_allowlist is then skipped entirely.
    # When set (= the PREVIOUS pepper), refresh-allowlist reads try the CURRENT
    # pepper/version first, then fall back to the PREVIOUS pepper at version N-1.
    REFRESH_TOKEN_PEPPER_PREVIOUS: str = ""

    # Integer version tag for the CURRENT pepper (increment by 1 each rotation).
    # Used as the ``vN`` segment in ``cache:refresh:v{N}:{digest}`` allowlist
    # keys.  Plain integer (not a secret) — deliberately NOT in REQUIRED_FIELDS.
    REFRESH_TOKEN_PEPPER_VERSION: int = 1

    # NOTE: ``JWT_EXPIRY_DAYS`` was DEPRECATED per the FE-D5 + FE-D6 amendments
    # and REMOVED during the §7 (`iam`) construction dispatch (2026-06-06).
    # Use ``ACCESS_TOKEN_TTL_SECONDS`` (access JWT lifetime) +
    # ``REFRESH_TOKEN_TTL_SECONDS`` (refresh cookie lifetime) instead.
    # See BACKEND_ARCHITECTURE.md §4.B amendment + §5.D table 3.

    # ── MSG91 (§5.D table 4) ───────────────────────────────────────────────
    MSG91_AUTH_KEY: str = ""
    MSG91_TEMPLATE_ID: str = ""

    # ── Razorpay (§5.D table 5) ────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""  # NEW — populated during iam dispatch

    # ── Gemini (§5.D table 6) ──────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ── GCS (§5.D table 7) ─────────────────────────────────────────────────
    GCS_BUCKET: str = ""
    GCS_PROJECT_ID: str = ""
    GCS_SIGNED_URL_TTL_SECONDS: int = 3600  # 1 h per MVP_ARCH §10.8

    # ── LangFuse (§5.D table 8) ────────────────────────────────────────────
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""  # NEW — populated during §6A dispatch
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # ── AI Ops (§5.D table 9) ──────────────────────────────────────────────
    AI_DAILY_BUDGET_INR: int = 500  # per MVP_ARCH §8 hard-stop
    AI_BUDGET_ALARM_THRESHOLD: float = 0.80  # 80% alarm before hard-stop

    # ── Cache (§5.D table 10) ──────────────────────────────────────────────
    CACHE_VERSION: str = "v1"  # bumps on quarterly Meesho corpus refresh

    # ── Audit (§5.D table 11) ──────────────────────────────────────────────
    AUDIT_PII_SALT: str = ""

    # ── Rate limits (§5.D table 12) ────────────────────────────────────────
    RL_PER_IP_PER_MINUTE: int = 120  # DDoS-class default; per-route overrides

    # ── CORS (§5.D table 13, NEVER-`["*"]` lock) ───────────────────────────
    # ``NoDecode`` lets the ``_parse_cors_origins`` validator below handle the
    # comma-separated string form — without it, pydantic-settings tries to
    # JSON-decode the raw env value before the field_validator runs.
    CORS_ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = Field(default_factory=list)
    CORS_ALLOW_CREDENTIALS: bool = True

    # ── App (§5.D table 14) ────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"

    # ── Feature flags (§3.2 — removed when feature ships to main) ─────────
    # FEATURE_SMART_PICKER_ENABLED: dev default True; staging default False
    # until 24h soak confirms top-5 recall ≥ 80% + per-call cost ≤ ₹0.05
    # (Decision D2 in docs/plans/features/smart-picker/FEATURE_PLAN.md).
    # Route returns 404 when False per Master Plan §3.2 backend protocol.
    FEATURE_SMART_PICKER_ENABLED: bool = True

    # FEATURE_IMAGE_PRECHECK_ENABLED: dev default True; staging default False
    # until 3 gates pass (watermark ≥ 85%, deterministic Pillow smoke,
    # GCS tenant-isolation verified) per Decision D2 in
    # docs/plans/features/image-precheck/FEATURE_PLAN.md.
    # POST /products/{id}/images returns 404 when False (Master Plan §3.2).
    # GET  /products/{id}/images returns empty list when False (read-only
    # endpoint; sellers may have legacy images — do NOT 404).
    FEATURE_IMAGE_PRECHECK_ENABLED: bool = True

    # FEATURE_CATALOG_FORM_ENABLED: dev default True; staging default False
    # (set via env) until the 5-condition soak passes
    # (Decision D2 in docs/plans/features/catalog-form/FEATURE_PLAN.md).
    # Catalog routes (/api/v1/products/*) return 404 when False per
    # Master Plan §3.2 backend protocol.
    FEATURE_CATALOG_FORM_ENABLED: bool = True

    # FEATURE_AI_AUTOFILL_ENABLED: dev default True; staging default False
    # (set via env) until soak passes
    # (Decision in docs/plans/features/ai-autofill/FEATURE_PLAN.md).
    # POST /api/v1/products/{id}/autofill returns 404 when False per
    # Master Plan §3.2 backend protocol (route guard owned by api-routes-builder).
    FEATURE_AI_AUTOFILL_ENABLED: bool = True

    # ── Validators ─────────────────────────────────────────────────────────
    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: object) -> object:
        """Accept comma-separated string OR JSON list OR Python list.

        K3s env injection uses comma-separated strings; ``.env`` files may use
        either form.  ``["*"]`` is rejected by ``_forbid_cors_wildcard`` below.
        """
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                return []
            # JSON array form: '["https://x.com","https://y.com"]'
            if stripped.startswith("["):
                import json

                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    return stripped  # let pydantic raise the type error
                return parsed
            # Comma-separated form: 'https://x.com,https://y.com'
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return v

    @model_validator(mode="after")
    def _forbid_cors_wildcard(self) -> "Settings":
        """§4.G amendment — CORS with credentials forbids `*` origin.

        Browsers reject ``Access-Control-Allow-Origin: *`` whenever
        ``Access-Control-Allow-Credentials: true`` is present.  Because the
        FE-D5 ratified auth pattern relies on credentialed cookies for the
        refresh-token flow, ``CORS_ALLOW_CREDENTIALS`` is locked at True and
        ``["*"]`` is structurally forbidden.
        """
        if "*" in self.CORS_ALLOWED_ORIGINS:
            raise SystemExit(
                "FATAL: CORS_ALLOWED_ORIGINS may not contain '*' "
                "(CORS with credentials forbids wildcard — §4.G amendment)"
            )
        return self

    @model_validator(mode="after")
    def _require_non_empty(self) -> "Settings":
        """Fail-fast: every Required: yes field in §5.D must be non-empty.

        ``str`` fields are required to be non-empty.  ``list[str]`` fields
        (CORS_ALLOWED_ORIGINS) are required to be non-empty as a list.
        Missing → ``SystemExit`` with the offending field name on stderr.
        """
        missing: list[str] = []
        for fname in REQUIRED_FIELDS:
            value = getattr(self, fname, None)
            if value is None or value == "" or value == []:
                missing.append(fname)
        if missing:
            joined = ", ".join(missing)
            raise SystemExit(
                f"FATAL: required env var(s) empty or unset: {joined} "
                f"(see BACKEND_ARCHITECTURE.md §5.D for the full registry)"
            )
        return self

    # ── Convenience properties (read-only) ─────────────────────────────────
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
    """Load Settings — swallow nothing.  SystemExit bubbles to the process."""
    try:
        return Settings()
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover — defensive boot trap
        # Pydantic ValidationErrors land here.  Print and re-raise as SystemExit
        # so the process dies cleanly rather than tracebacking.
        print(f"FATAL: Settings load failed — {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


settings: Settings = _load_settings()
"""Module-level singleton — every other module imports this.

Locked rule: NO module instantiates ``Settings()`` again.  ``from
app.shared.config import settings`` is the only valid access path.
"""
