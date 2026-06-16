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


# ── L_iam_1 known-deferred auth ids: DEBUG-not-WARNING noise suppression ─────
@pytest.mark.parametrize(
    "deferred_id",
    ["auth.token_missing", "auth.token_expired", "auth.user_not_found"],
)
def test_deferred_auth_id_logs_debug_not_warning(
    deferred_id: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """L_iam_1 2-segment auth ids log at DEBUG, not WARNING.

    Behaviour (verbatim fallback) is UNCHANGED — the id is still returned —
    only the log level changes so the per-401 noise is silenced while
    L_iam_1 is deferred. These ids are intentionally absent from the
    3-segment-locked catalog.
    """
    assert deferred_id not in VALIDATION_MESSAGES
    with caplog.at_level(logging.DEBUG, logger="app.i18n.resolver"):
        result = resolve(deferred_id, locale="en")
    # Verbatim fallback unchanged.
    assert result == deferred_id
    # The missing_key line is present...
    missing_records = [
        r
        for r in caplog.records
        if "i18n.resolver.missing_key" in r.getMessage()
        and deferred_id in r.getMessage()
    ]
    assert missing_records, "expected a missing_key log line for the deferred id"
    # ...and every such line is at DEBUG, never WARNING.
    assert all(r.levelno == logging.DEBUG for r in missing_records)


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
