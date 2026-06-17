"""
Tests for section-2 (smart-picker) i18n error message contract — Plan 2-W1.
"""
import re

import pytest

# ── 3-segment regex ──────────────────────────────────────────────────────────
_THREE_SEG = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2}$")


# ── Registry imports ──────────────────────────────────────────────────────────
def _load_registry():
    from app.i18n.messages_en import VALIDATION_MESSAGES
    return VALIDATION_MESSAGES


def _load_exception_classes():
    from app.modules.category.exceptions import (
        BrowseQueryInvalidError,
        CategoryNotFoundError,
        FieldEnumNotFoundError,
        SuggestQueryInvalidError,
    )
    from app.core.middleware.rate_limit_mw import RateLimitExceededError
    return [
        SuggestQueryInvalidError,
        CategoryNotFoundError,
        FieldEnumNotFoundError,
        BrowseQueryInvalidError,
        RateLimitExceededError,
    ]


# ── Test 1: all registry keys match 3-segment regex ──────────────────────────
def test_all_registry_keys_are_three_segment():
    registry = _load_registry()
    bad_keys = [k for k in registry if not _THREE_SEG.match(k)]
    assert bad_keys == [], f"Registry keys violate 3-segment rule: {bad_keys}"


# ── Test 2: exception classes carry compliant IDs ────────────────────────────
def test_exception_class_validation_message_ids_are_three_segment():
    for cls in _load_exception_classes():
        msg_id = getattr(cls, "validation_message_id", None) or getattr(
            cls, "default_validation_message_id", None
        )
        assert msg_id is not None, f"{cls.__name__} has no validation_message_id"
        assert _THREE_SEG.match(msg_id), (
            f"{cls.__name__}.validation_message_id='{msg_id}' violates 3-segment rule"
        )


# ── Test 3: the 5 expected IDs are registered ─────────────────────────────────
@pytest.mark.parametrize("msg_id", [
    "validation.suggest_q.too_short_or_long",
    "category.lookup.not_found",
    "category.field_enum.not_found",
    "validation.browse.invalid_pagination",
    "rate_limit.window.exceeded",
])
def test_expected_ids_are_registered(msg_id: str):
    registry = _load_registry()
    assert msg_id in registry, f"'{msg_id}' missing from VALIDATION_MESSAGES"


# ── Test 4: fallback-flag cases are NOT registered (they are 200 + fallback_offered) ──
@pytest.mark.parametrize("absent_id", [
    "smart_picker.ai.unavailable",
    "smart_picker.budget.exceeded",
])
def test_fallback_flag_ids_are_absent_from_registry(absent_id: str):
    registry = _load_registry()
    assert absent_id not in registry, (
        f"'{absent_id}' must NOT be in VALIDATION_MESSAGES — "
        "these are 200+fallback_offered paths, not error envelopes"
    )


# ── Test 5: suggest_q copy reflects the enforced 1-500 bound ──────────────────
def test_suggest_q_copy_matches_enforced_bounds():
    registry = _load_registry()
    copy = registry.get("validation.suggest_q.too_short_or_long", "")
    assert "1" in copy and "500" in copy, (
        f"suggest_q copy must mention the enforced 1–500 bound, got: '{copy}'"
    )
    assert "2" not in copy or "60" not in copy, (
        f"suggest_q copy must NOT mention the old 2–60 bound, got: '{copy}'"
    )
