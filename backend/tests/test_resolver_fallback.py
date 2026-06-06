"""§5A.I — resolver fallback chain locked contract.

Asserts the locked fallback order::

    1. requested locale → resolved string
    2. en (canonical fallback) → resolved string
    3. message_id verbatim (debug-hint tier)

V1 ships only ``"en"``; tests simulate a non-en locale request to verify
the chain degrades correctly to ``"en"`` (V1.5 forward-compat) and then
to verbatim (last-resort tier).
"""

from __future__ import annotations

import logging

import pytest

from app.i18n.messages_en import VALIDATION_MESSAGES
from app.i18n.resolver import resolve


def test_en_locale_known_id_returns_english_string() -> None:
    """Tier 1 — requested locale registers the ID."""
    # Pick a stable known key from the registry.
    known = "server.internal.error"
    assert known in VALIDATION_MESSAGES
    result = resolve(known, locale="en")
    assert result == VALIDATION_MESSAGES[known]


def test_default_locale_is_en() -> None:
    """Resolver default ``locale`` parameter is ``\"en\"`` per §5A.I."""
    known = "server.internal.error"
    assert resolve(known) == VALIDATION_MESSAGES[known]


def test_non_en_locale_missing_id_falls_back_to_en() -> None:
    """Tier 2 — non-en locale not present in registry → en fallback.

    V1 only registers ``en``; passing ``hi`` exercises the fallback path
    that V1.5 will rely on when ``messages_hi.py`` ships partial coverage.
    """
    known = "validation.phone.invalid_format"
    assert known in VALIDATION_MESSAGES
    result = resolve(known, locale="hi")
    assert result == VALIDATION_MESSAGES[known]


def test_unknown_id_in_en_returns_verbatim_id() -> None:
    """Tier 3 — unknown id with no fallback in any locale → verbatim."""
    mid = "totally.unknown.message_id"
    assert mid not in VALIDATION_MESSAGES
    assert resolve(mid, locale="en") == mid


def test_unknown_id_non_en_locale_returns_verbatim_id() -> None:
    """Tier 3 also fires when the en fallback misses for a non-en locale."""
    mid = "totally.unknown.message_id"
    assert resolve(mid, locale="ta") == mid


def test_unknown_id_logs_missing_key_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tier 3 emits a ``i18n.resolver.missing_key`` log line for observability.

    §6A/§19 observability counts these as a metric; the substring is the
    stable contract.
    """
    mid = "another.unknown.message_id"
    with caplog.at_level(logging.WARNING, logger="app.i18n.resolver"):
        result = resolve(mid, locale="en")
    assert result == mid
    assert any(
        "i18n.resolver.missing_key" in record.getMessage()
        and mid in record.getMessage()
        for record in caplog.records
    )


def test_unregistered_locale_falls_back_to_en() -> None:
    """An entirely unknown locale code falls through tier 1 to tier 2."""
    known = "catalog.product.not_found"
    assert known in VALIDATION_MESSAGES
    # 'fr' is not registered in V1 _REGISTRIES; should still resolve via en.
    assert resolve(known, locale="fr") == VALIDATION_MESSAGES[known]
