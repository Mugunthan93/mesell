"""§5A.I — generic-family validation fallback (resolver Step-2b).

Per-field validation ids (``validation.<field>.<rule>``) that have no
bespoke registry entry resolve to the ``validation.generic.<rule>`` family
string. This avoids minting a catalog key for every dynamic catalog field
while still returning a human-readable message (not the verbatim id) for the
common rules (``invalid_enum_value`` / ``invalid_type`` / ``too_long`` /
``invalid_url``).

The fallback is a RESOLVED tier — it must NOT bump the ``i18n.resolver.
missing_key`` counter and must NOT emit a WARNING.
"""

from __future__ import annotations

import logging

import pytest

from app.i18n.messages_en import VALIDATION_MESSAGES
from app.i18n.resolver import resolve

pytestmark = pytest.mark.unit


# ── the generic family strings exist and are 3-segment-clean ────────────────
@pytest.mark.parametrize(
    "rule",
    ["invalid_enum_value", "invalid_type", "too_long", "invalid_url"],
)
def test_generic_family_keys_registered(rule: str) -> None:
    """Each generic-family key is present in the registry."""
    assert f"validation.generic.{rule}" in VALIDATION_MESSAGES


# ── per-field id falls back to the generic family string ────────────────────
def test_per_field_id_falls_back_to_generic_string(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``resolve('validation.foo.invalid_enum_value')`` == generic string.

    No missing-key WARNING and no verbatim return — this is a RESOLVED tier.
    """
    per_field_id = "validation.foo.invalid_enum_value"
    generic_id = "validation.generic.invalid_enum_value"
    assert per_field_id not in VALIDATION_MESSAGES
    assert generic_id in VALIDATION_MESSAGES

    with caplog.at_level(logging.DEBUG, logger="app.i18n.resolver"):
        result = resolve(per_field_id, locale="en")

    # Resolved to the generic family string (not verbatim).
    assert result == VALIDATION_MESSAGES[generic_id]
    assert result != per_field_id
    # No missing_key log line at all (DEBUG or WARNING).
    assert not [
        r for r in caplog.records if "i18n.resolver.missing_key" in r.getMessage()
    ]


@pytest.mark.parametrize(
    "field,rule",
    [
        ("size_in_ltrs", "invalid_enum_value"),
        ("weight", "invalid_type"),
        ("brand", "too_long"),
        ("source_link", "invalid_url"),
    ],
)
def test_each_per_field_rule_resolves_to_its_generic_family(
    field: str, rule: str
) -> None:
    """Every supported rule maps a dynamic field id to its generic string."""
    per_field_id = f"validation.{field}.{rule}"
    generic_id = f"validation.generic.{rule}"
    assert per_field_id not in VALIDATION_MESSAGES
    assert resolve(per_field_id) == VALIDATION_MESSAGES[generic_id]


# ── generic id resolves to itself (no recursion) ────────────────────────────
def test_generic_id_returns_its_own_string_no_recursion() -> None:
    """``resolve('validation.generic.invalid_enum_value')`` == own string.

    The generic id hits the en registry at Step-2 directly; Step-2b must not
    rewrite it to itself or recurse.
    """
    generic_id = "validation.generic.invalid_enum_value"
    assert resolve(generic_id) == VALIDATION_MESSAGES[generic_id]


# ── a per-field id whose rule has no generic family still warns verbatim ────
def test_per_field_id_with_unknown_rule_falls_through_to_verbatim(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """No generic family for the rule → genuine missing key → verbatim WARN."""
    mid = "validation.foo.some_bespoke_rule"
    assert mid not in VALIDATION_MESSAGES
    assert "validation.generic.some_bespoke_rule" not in VALIDATION_MESSAGES
    with caplog.at_level(logging.WARNING, logger="app.i18n.resolver"):
        result = resolve(mid, locale="en")
    assert result == mid
    assert [
        r
        for r in caplog.records
        if "i18n.resolver.missing_key" in r.getMessage() and mid in r.getMessage()
    ]


# ── auth.token_missing: locked L_iam_1 verbatim behaviour is UNCHANGED ───────
def test_auth_token_missing_unchanged_verbatim_l_iam_1() -> None:
    """``auth.token_missing`` is NOT a 3-segment key and is NOT generic-family.

    Per the locked L_iam_1 deferral (see ``resolver._DEFERRED_DEBUG_MISSING_KEYS``)
    the 2-segment auth ids remain verbatim-at-DEBUG. This fix does NOT change
    that — adding the key to the 3-segment-locked catalog would break §5A.H
    Contract 10. See the PR deviation note.
    """
    assert "auth.token_missing" not in VALIDATION_MESSAGES
    # Step-2b only fires for ``validation.*`` ids, so auth ids are untouched.
    assert resolve("auth.token_missing") == "auth.token_missing"


# ── existing q.missing key is unchanged (no duplicate, still resolves) ──────
def test_q_missing_still_resolves_unchanged() -> None:
    """``validation.q.missing`` pre-exists; this fix must not disturb it."""
    assert "validation.q.missing" in VALIDATION_MESSAGES
    # It is a real 3-segment key, so it resolves at Step-2 (not via Step-2b).
    assert resolve("validation.q.missing") == VALIDATION_MESSAGES["validation.q.missing"]
