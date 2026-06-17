"""svc-iam services-builder SCAFFOLD validation (Phase B, services-builder slice).

These tests validate ONLY the surfaces this services-builder dispatch owns:
repository / domain / exceptions + the vendored trimmed ``shared/*`` + ``core``
(errors / tenancy / metrics / 6-mw chain) + the ``i18n`` subset + the
``shared/models`` binding.  They deliberately do NOT import ``app.service`` or
``app.core.auth`` (auth-builder's byte-for-byte files, delivered on this SAME
branch AFTER this scaffold) — and they do NOT import ``app.main`` (which
transitively imports ``app.core.auth`` via the vendored ``auth_mw``).  The full
hybrid-mode FE-D5 round-trip test (``test_iam_extraction.py``) is LEAD-owned
(Phase C).

The single allowed seam-dependency: ``exceptions.py`` and ``core/tenancy.py``
import ``app.core.errors.MeesellError`` (present in this scaffold).
"""

from __future__ import annotations

import importlib

# conftest.py has already populated the env before this module imports.


# ── Trimmed Settings — field presence + ABSENCE ─────────────────────────────
def test_settings_has_iam_required_fields():
    from app.shared.config import settings

    # DB + Valkey
    assert settings.DATABASE_URL
    assert settings.VALKEY_URL
    # JWT sign + verify (iam ISSUES tokens)
    assert settings.JWT_SECRET
    assert settings.JWT_ALGORITHM == "HS256"
    assert settings.ACCESS_TOKEN_TTL_SECONDS > 0
    assert settings.REFRESH_TOKEN_TTL_SECONDS > 0
    # FE-D5 dual-pepper allowlist trio
    assert settings.REFRESH_TOKEN_PEPPER
    assert hasattr(settings, "REFRESH_TOKEN_PEPPER_PREVIOUS")
    assert settings.REFRESH_TOKEN_PEPPER_VERSION >= 1
    # MSG91 (OTP send) + Razorpay (webhook HMAC)
    assert settings.MSG91_AUTH_KEY
    assert settings.MSG91_TEMPLATE_ID
    assert settings.RAZORPAY_KEY_ID
    assert settings.RAZORPAY_KEY_SECRET
    assert settings.RAZORPAY_WEBHOOK_SECRET
    # Audit + CORS + App
    assert settings.AUDIT_PII_SALT
    assert settings.APP_ENV == "development"


def test_settings_does_not_carry_ai_storage_or_shim_fields():
    """iam owns no AI / storage and makes no outbound shim (§0.4 all-✗)."""
    from app.shared.config import settings

    for absent in (
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_HOST",
        "GCS_BUCKET",
        "GCS_PROJECT_ID",
        "AI_DAILY_BUDGET_INR",
        "CACHE_VERSION",
        "MONOLITH_INTERNAL_BASE_URL",  # iam is all-✗ — no shim target
    ):
        assert not hasattr(settings, absent), f"Settings unexpectedly carries {absent}"


def test_required_fields_registry_matches_iam():
    from app.shared.config import REQUIRED_FIELDS

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
        "AUDIT_PII_SALT",
        "CORS_ALLOWED_ORIGINS",
        "APP_ENV",
    }
    assert set(REQUIRED_FIELDS) == expected


# ── Valkey — DB 0 factory + Lua helpers, NO broker/results ──────────────────
def test_valkey_surface_is_db0_plus_lua_helpers():
    import app.shared.valkey as vk

    assert hasattr(vk, "get_valkey_otp")
    assert hasattr(vk, "load_lua_script")  # required by vendored core/auth.py
    assert hasattr(vk, "eval_lua_script")
    assert hasattr(vk, "aclose_all")
    # NO Celery — broker (DB 1) / result-backend (DB 2) factories NOT vendored
    assert not hasattr(vk, "get_valkey_broker")
    assert not hasattr(vk, "get_valkey_results")
    assert not hasattr(vk, "get_valkey_cache")


# ── i18n subset — iam IDs + 3 auth.token.* + 3 cross-cutting ────────────────
def test_i18n_subset_carries_iam_ids():
    from app.i18n.messages_en import VALIDATION_MESSAGES

    iam_ids = {
        "validation.phone.invalid_format",
        "validation.otp.invalid_format",
        "validation.webhook.malformed_payload",
        "auth.otp.invalid",
        "auth.otp.attempts_exceeded",
        "auth.msg91.unavailable",
        "auth.refresh.invalid",
        "auth.webhook.signature_invalid",
    }
    auth_token_ids = {"auth.token.missing", "auth.token.expired", "auth.user.not_found"}
    cross_cutting = {
        "tenancy.cross_user.access",
        "plan.limit.exceeded",
        "server.internal.error",
    }
    keys = set(VALIDATION_MESSAGES)
    assert iam_ids <= keys
    assert auth_token_ids <= keys
    assert cross_cutting <= keys
    # subset only — the full 55-ID monolith registry is NOT vendored
    assert len(keys) == len(iam_ids | auth_token_ids | cross_cutting) == 14


def test_i18n_resolver_resolves_an_iam_id():
    from app.i18n.resolver import resolve

    msg = resolve("auth.otp.invalid")
    assert "OTP" in msg and msg != "auth.otp.invalid"


# ── ORM models — schema binding ─────────────────────────────────────────────
def test_user_bound_to_iam_schema_no_relationships():
    from app.shared.models.user import User

    assert User.__table__.schema == "iam"
    # all sibling relationships dropped (cross-schema FKs dropped — §0.7)
    assert len(User.__mapper__.relationships) == 0


def test_audit_event_bound_to_public_schema():
    from app.shared.models import AuditEvent

    assert AuditEvent.__table__.schema == "public"  # cross-schema write target


# ── metrics — the 3 symbols iam emits (incl. AUTH_TOKEN_REFRESH_FAILED) ─────
def test_metrics_carries_auth_refresh_failed():
    from app.core import metrics

    assert hasattr(metrics, "HTTP_REQUEST_DURATION")
    assert hasattr(metrics, "HTTP_REQUESTS_TOTAL")
    # service.py (auth-builder's file) increments this on rotation failure
    assert hasattr(metrics, "AUTH_TOKEN_REFRESH_FAILED")


# ── repository / domain / exceptions — import + shape ───────────────────────
def test_repository_imports_and_dpdp_noop_preserved():
    import inspect

    import app.repository as repo

    assert hasattr(repo, "find_user_by_phone")
    assert hasattr(repo, "upsert_user_on_login")
    assert hasattr(repo, "get_user_by_id")
    assert hasattr(repo, "update_plan")
    # DPDP no-op preserved VERBATIM (§0.8) — the no-column guard is still present
    src = inspect.getsource(repo.upsert_user_on_login)
    assert 'hasattr(user, "dpdp_consented_at")' in src
    assert "dpdp_consent.skipped_no_column" in src


def test_domain_eight_frozen_dataclasses():
    import dataclasses

    import app.domain as domain

    names = [
        "OtpRecord",
        "RefreshAllowlistEntry",
        "SendOtpResult",
        "VerifyOtpResult",
        "RotateRefreshResult",
        "RevokeResult",
        "UserProfile",
        "WebhookCaptureResult",
    ]
    assert set(domain.__all__) == set(names)
    for n in names:
        cls = getattr(domain, n)
        assert dataclasses.is_dataclass(cls)
        assert cls.__dataclass_params__.frozen is True


def test_exceptions_nine_class_iam_error_hierarchy():
    import app.exceptions as exc
    from app.core.errors import MeesellError

    classes = [
        "IamError",
        "InvalidPhoneFormatError",
        "InvalidOtpFormatError",
        "MalformedWebhookPayloadError",
        "OtpInvalidError",
        "OtpAttemptsExceededError",
        "RefreshInvalidError",
        "WebhookSignatureInvalidError",
        "Msg91UnavailableError",
    ]
    assert set(exc.__all__) == set(classes)
    assert issubclass(exc.IamError, MeesellError)
    # every concrete subclass carries a 3-segment validation_message_id
    for n in classes[1:]:
        cls = getattr(exc, n)
        mid = cls.validation_message_id
        assert mid.count(".") == 2, f"{n} message_id {mid!r} is not 3-segment"


# ── byte-for-byte vendor parity vs the monolith (the §16.G invariant) ───────
def test_iam_owned_files_are_byte_identical_to_monolith():
    """repository / domain / exceptions vendor byte-for-byte (path-stable imports)."""
    import pathlib

    svc_root = pathlib.Path(__file__).resolve().parents[1] / "app"
    # backend/services/svc-iam/app -> backend/app/modules/iam
    mono_root = svc_root.parents[2] / "app" / "modules" / "iam"
    for fname in ("repository.py", "domain.py", "exceptions.py"):
        svc_txt = (svc_root / fname).read_text()
        mono_txt = (mono_root / fname).read_text()
        assert svc_txt == mono_txt, f"{fname} drifted from the monolith vendor source"


def test_no_extracted_clients_and_no_request_context_mw():
    """iam is all-✗ (§0.4) — no outbound shim scaffolding."""
    import pathlib

    app_root = pathlib.Path(__file__).resolve().parents[1] / "app"
    assert not (app_root / "core" / "extracted_clients").exists()
    assert not (app_root / "core" / "middleware" / "request_context_mw.py").exists()
    # also no Celery (iam has no tasks.py — §0.2).
    assert not (app_root / "workers").exists()
    # service.py + core/auth.py are now LANDED by the auth-builder on this SAME
    # branch (Phase B heavy lift) — they MUST exist (the scaffold's earlier
    # "not yet present" assertion was a placeholder pending this dispatch).
    assert (app_root / "service.py").exists()  # auth-builder's file (landed)
    assert (app_root / "core" / "auth.py").exists()  # auth-builder's file (landed)


def test_core_errors_importable_without_auth():
    """core/errors + tenancy + resolver import without core/auth.py present."""
    for mod in ("app.core.errors", "app.core.tenancy", "app.i18n.resolver"):
        importlib.import_module(mod)
