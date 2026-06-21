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

pytestmark = pytest.mark.unit


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


# ── L_iam_1 RESOLVED: core/auth.py now raises 3-segment auth ids ─────────────
@pytest.mark.parametrize(
    "auth_id",
    ["auth.token.missing", "auth.token.expired", "auth.user.not_found"],
)
def test_auth_ids_resolve_to_human_strings(
    auth_id: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The 3-segment auth ids raised by ``core/auth.py`` resolve to human copy.

    Closes L_iam_1: ``core/auth.py`` migrated from 2-segment legacy ids
    (``auth.token_missing``) to the 3-segment catalog ids
    (``auth.token.missing``) that exist in ``messages_en``. The resolver now
    returns the human string — NOT the verbatim id — and emits NO missing_key
    line. The 2-segment deferral allowlist was deleted in lock-step.
    """
    assert auth_id in VALIDATION_MESSAGES
    with caplog.at_level(logging.DEBUG, logger="app.i18n.resolver"):
        result = resolve(auth_id, locale="en")
    # Resolved to the human catalog string, NOT the verbatim id.
    assert result == VALIDATION_MESSAGES[auth_id]
    assert result != auth_id
    # No missing_key telemetry for a registered key.
    assert not [
        r
        for r in caplog.records
        if "i18n.resolver.missing_key" in r.getMessage()
        and auth_id in r.getMessage()
    ]


def test_real_missing_key_still_warns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A genuine (non-allowlisted) missing key still WARNs loudly."""
    mid = "genuinely.unknown.message_id"
    assert mid not in VALIDATION_MESSAGES
    with caplog.at_level(logging.DEBUG, logger="app.i18n.resolver"):
        result = resolve(mid, locale="en")
    assert result == mid
    warn_records = [
        r
        for r in caplog.records
        if "i18n.resolver.missing_key" in r.getMessage()
        and mid in r.getMessage()
    ]
    assert warn_records
    assert all(r.levelno == logging.WARNING for r in warn_records)
