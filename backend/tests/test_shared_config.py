"""§5.D acceptance tests — shared.config Settings + env-var registry.

Verifies the locked surface area:
  * Settings field surface matches §5.D (11 grouped tables + App).
  * ``REQUIRED_FIELDS`` registry enforces fail-fast SystemExit at boot when
    any required field is empty.
  * CORS wildcard (``["*"]``) is structurally forbidden per §4.G amendment.
  * Comma-separated CORS string parses to ``list[str]`` via the field
    validator.
  * ``JWT_EXPIRY_DAYS`` exists for legacy compatibility and is documented as
    DEPRECATED.
  * ACCESS_TOKEN_TTL_SECONDS + REFRESH_TOKEN_TTL_SECONDS + REFRESH_TOKEN_PEPPER
    are present (FE-D5 ratification).
  * The canonical model registry import path resolves all 13 classes.

These tests instantiate ``Settings`` directly with monkeypatched environments,
bypassing the module-level singleton.  They do NOT mutate ``settings`` itself.
"""

from __future__ import annotations

import importlib

import pytest
from pydantic_settings import SettingsConfigDict

from app.shared.config import REQUIRED_FIELDS, Settings, settings

pytestmark = pytest.mark.unit


# ───────────────────────────────────────────────────────────────────────────
# Test helpers
# ───────────────────────────────────────────────────────────────────────────


def _good_env(**overrides: str) -> dict[str, str]:
    """Build a Settings env dict satisfying every required field.

    Each REQUIRED field gets a non-empty placeholder; CORS_ALLOWED_ORIGINS
    gets a comma-separated string the field validator can parse.
    """
    base: dict[str, str] = {
        "DATABASE_URL": "postgresql+asyncpg://u:p@localhost/db",
        "VALKEY_URL": "redis://localhost:6379/0",
        "JWT_SECRET": "x" * 32,
        "REFRESH_TOKEN_PEPPER": "y" * 32,
        "MSG91_AUTH_KEY": "msg91-key",
        "MSG91_TEMPLATE_ID": "msg91-template",
        "RAZORPAY_KEY_ID": "rzp_test_xxx",
        "RAZORPAY_KEY_SECRET": "rzp-secret",
        "RAZORPAY_WEBHOOK_SECRET": "rzp-webhook",
        "GEMINI_API_KEY": "AIza_xxx",
        "GCS_BUCKET": "meesell-dev",
        "GCS_PROJECT_ID": "gcp-project",
        "LANGFUSE_PUBLIC_KEY": "lf-public",
        "LANGFUSE_SECRET_KEY": "lf-secret",
        "AUDIT_PII_SALT": "audit-salt",
        "CORS_ALLOWED_ORIGINS": "https://dev.mesell.xyz,https://www.mesell.xyz",
        "APP_ENV": "development",
    }
    base.update(overrides)
    return base


def _build_settings(
    monkeypatch: pytest.MonkeyPatch, env: dict[str, str]
) -> Settings:
    """Construct a Settings instance against a fully-isolated env.

    Wraps construction the same way the production ``_load_settings`` helper
    does: pydantic ``ValidationError`` is converted to ``SystemExit``.  This
    keeps the test contract uniform — "empty required field → SystemExit" —
    regardless of whether the field type is plain ``str`` (caught by our
    ``_require_non_empty`` validator) or a ``Literal`` (caught by pydantic
    itself before our validator runs).
    """
    for fname in Settings.model_fields:
        monkeypatch.delenv(fname, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    # Build a Settings subclass that skips the dotenv file so the test is
    # not influenced by repo-level `.env`.
    class _IsolatedSettings(Settings):
        model_config = SettingsConfigDict(
            env_file=None,
            case_sensitive=True,
            extra="ignore",
        )

    try:
        return _IsolatedSettings()
    except SystemExit:
        raise
    except Exception as exc:
        # Mirror _load_settings: convert ValidationError → SystemExit so the
        # contract "missing/invalid required → SystemExit" holds uniformly.
        raise SystemExit(str(exc)) from exc


# ───────────────────────────────────────────────────────────────────────────
# Field surface — required-field registry coverage
# ───────────────────────────────────────────────────────────────────────────


def test_required_fields_registry_matches_5d_table() -> None:
    """REQUIRED_FIELDS contains exactly the §5.D Required: yes rows."""
    expected = {
        "DATABASE_URL",
        "VALKEY_URL",
        "JWT_SECRET",
        "REFRESH_TOKEN_PEPPER",
        "MSG91_AUTH_KEY",
        "MSG91_TEMPLATE_ID",
        "RAZORPAY_KEY_ID",
        "RAZORPAY_KEY_SECRET",
        "RAZORPAY_WEBHOOK_SECRET",
        "GEMINI_API_KEY",
        "GCS_BUCKET",
        "GCS_PROJECT_ID",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "AUDIT_PII_SALT",
        "CORS_ALLOWED_ORIGINS",
        "APP_ENV",
    }
    assert set(REQUIRED_FIELDS) == expected


def test_all_required_fields_are_declared_on_settings() -> None:
    """Every entry in REQUIRED_FIELDS MUST exist as a Settings field."""
    declared = set(Settings.model_fields)
    for fname in REQUIRED_FIELDS:
        assert fname in declared, f"{fname} missing from Settings class"


def test_jwt_expiry_days_field_removed_by_iam_dispatch() -> None:
    """``JWT_EXPIRY_DAYS`` was deprecated by FE-D5 and REMOVED during the §7
    iam construction dispatch (2026-06-06). Verify it is NOT in the Settings
    class — any resurrection MUST be flagged at PR time.

    Replacements: ``ACCESS_TOKEN_TTL_SECONDS`` + ``REFRESH_TOKEN_TTL_SECONDS``.
    """
    assert "JWT_EXPIRY_DAYS" not in Settings.model_fields
    assert "JWT_EXPIRY_DAYS" not in REQUIRED_FIELDS
    # Replacements MUST be present.
    assert "ACCESS_TOKEN_TTL_SECONDS" in Settings.model_fields
    assert "REFRESH_TOKEN_TTL_SECONDS" in Settings.model_fields


def test_fe_d5_jwt_fields_present_with_locked_defaults() -> None:
    """ACCESS_TOKEN_TTL_SECONDS + REFRESH_TOKEN_TTL_SECONDS defaults locked."""
    fields = Settings.model_fields
    assert fields["ACCESS_TOKEN_TTL_SECONDS"].default == 900
    assert fields["REFRESH_TOKEN_TTL_SECONDS"].default == 604800


def test_cache_version_default_v1() -> None:
    """CACHE_VERSION default locked at 'v1' per §5.D."""
    assert Settings.model_fields["CACHE_VERSION"].default == "v1"


# ───────────────────────────────────────────────────────────────────────────
# Happy path — full env satisfies the validator
# ───────────────────────────────────────────────────────────────────────────


def test_full_env_loads_without_systemexit(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fully-populated env loads Settings cleanly."""
    s = _build_settings(monkeypatch, _good_env())
    assert s.APP_ENV == "development"
    assert s.CORS_ALLOWED_ORIGINS == [
        "https://dev.mesell.xyz",
        "https://www.mesell.xyz",
    ]


# ───────────────────────────────────────────────────────────────────────────
# Fail-fast — every required field triggers SystemExit when empty
# ───────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("missing", REQUIRED_FIELDS)
def test_missing_required_field_systemexits(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    """SystemExit fires when ANY required field is empty (§5.D locked)."""
    env = _good_env()
    env[missing] = ""  # blank out the one under test
    with pytest.raises(SystemExit) as excinfo:
        _build_settings(monkeypatch, env)
    # The error message must name the offending field
    assert missing in str(excinfo.value)


# ───────────────────────────────────────────────────────────────────────────
# CORS wildcard lock + comma-separated parsing
# ───────────────────────────────────────────────────────────────────────────


def test_cors_wildcard_systemexits(monkeypatch: pytest.MonkeyPatch) -> None:
    """CORS_ALLOWED_ORIGINS=* is structurally forbidden per §4.G amendment."""
    env = _good_env(CORS_ALLOWED_ORIGINS="*")
    with pytest.raises(SystemExit) as excinfo:
        _build_settings(monkeypatch, env)
    assert "CORS_ALLOWED_ORIGINS" in str(excinfo.value)
    assert "*" in str(excinfo.value)


def test_cors_comma_separated_parses_to_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Comma-separated string env value parses to a ``list[str]``."""
    s = _build_settings(
        monkeypatch,
        _good_env(CORS_ALLOWED_ORIGINS="https://a.test, https://b.test ,https://c.test"),
    )
    assert s.CORS_ALLOWED_ORIGINS == [
        "https://a.test",
        "https://b.test",
        "https://c.test",
    ]


def test_cors_json_array_form_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    """JSON array env value parses to a ``list[str]``."""
    s = _build_settings(
        monkeypatch,
        _good_env(
            CORS_ALLOWED_ORIGINS='["https://a.test", "https://b.test"]',
        ),
    )
    assert s.CORS_ALLOWED_ORIGINS == ["https://a.test", "https://b.test"]


# ───────────────────────────────────────────────────────────────────────────
# Module-level singleton smoke test (live .env on disk)
# ───────────────────────────────────────────────────────────────────────────


def test_module_singleton_loaded_from_dotenv() -> None:
    """The module-level ``settings`` singleton boots against the on-disk .env."""
    assert settings.APP_ENV in {"development", "staging", "production"}
    assert settings.CORS_ALLOWED_ORIGINS  # non-empty
    assert "*" not in settings.CORS_ALLOWED_ORIGINS


# ───────────────────────────────────────────────────────────────────────────
# Canonical model registry import path resolves all 13 names (§5.E)
# ───────────────────────────────────────────────────────────────────────────


def test_canonical_models_import_path_resolves_13() -> None:
    """`from app.shared.models import ...` MUST resolve all 13 ORM classes."""
    mod = importlib.import_module("app.shared.models")
    for name in (
        "User",
        "SellerProfile",
        "Template",
        "Category",
        "FieldEnumValue",
        "FieldAlias",
        "Catalog",
        "Product",
        "ProductImage",
        "PricingCalc",
        "Export",
        "AuditEvent",
        "ProductDraft",
    ):
        assert hasattr(mod, name), f"{name} not exported from app.shared.models"
