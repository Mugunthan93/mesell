"""§19.C Contract 10 — pytest wrapper for VALIDATION_MESSAGES regex scanner.

Two assertions per the §19 construction protocol:

1. **Happy path** — :func:`check_message_id_regex.scan` returns an empty
   list against the live ``app/i18n/messages_en.py`` registry.
2. **Counter-example** — a synthetic key like ``"catalog.draftMissing"``
   (camelCase) or ``"auth.token_missing"`` (2 segments) MUST be classified
   as a violation by :func:`check_message_id_regex._classify`.

This module is a thin wrapper over :mod:`tests.lint.check_message_id_regex`;
the belt-and-braces ``tests/test_messages_en_id_regex.py`` covers the same
surface with parametrised per-key assertions and adds 4 additional shape
checks (no hyphens, no uppercase, exactly 3 segments, non-empty values).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from tests.lint import check_message_id_regex as scanner


@pytest.mark.smoke
def test_message_id_regex_clean_on_live_registry() -> None:
    """Every VALIDATION_MESSAGES key matches the §5A.H 3-segment regex."""
    violations = scanner.scan()
    assert violations == [], (
        "§19.C Contract 10 FAIL on live registry:\n"
        + "\n".join(v.render() for v in violations)
    )


def test_message_id_regex_flags_two_segment_key() -> None:
    """A 2-segment key (e.g. legacy `auth.token_missing`) MUST be flagged.

    Mirrors the L_iam_1 latent (per STATUS_BACKEND): ``core/auth.py`` raises
    2-segment IDs but §5A.H requires 3. This test pins the regex behavior so
    a future migration to 3-segment IDs is verified.
    """
    reason = scanner._classify("auth.token_missing")
    assert reason is not None
    assert "2 segments" in reason or "3" in reason


def test_message_id_regex_flags_camel_case_key() -> None:
    """A camelCase key (e.g. `catalog.draftMissing`) MUST be flagged."""
    reason = scanner._classify("catalog.draftMissing")
    assert reason is not None


def test_message_id_regex_flags_hyphenated_key() -> None:
    """A hyphenated key (e.g. `auth.token-missing`) MUST be flagged."""
    reason = scanner._classify("auth.token-missing")
    assert reason is not None


def test_message_id_regex_accepts_valid_3_segment_key() -> None:
    """A canonical 3-segment snake_case key MUST be accepted."""
    assert scanner._classify("validation.product_name.too_short") is None
    assert scanner._classify("auth.token.missing") is None
    assert scanner._classify("export.round_trip.mismatch") is None


def test_message_id_regex_source_is_5ah_locked() -> None:
    """The regex SOURCE string MUST be the §5A.H locked shape.

    Pins the regex string itself so a stealth weakening (e.g. allowing 4
    segments) does not silently slip through PR review.
    """
    assert scanner.MESSAGE_ID_REGEX_SOURCE == (
        r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$"
    )
