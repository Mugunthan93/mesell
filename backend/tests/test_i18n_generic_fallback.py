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


# ── newly-shipped Pydantic-native generic rules (the generic-missing fix) ───
# These rule strings are the raw Pydantic-v2 error ``type`` values that
# ``core/errors.py`` turns into per-field ids ``validation.<field>.<type>``.
# Before this fix only ``invalid_enum_value`` / ``invalid_type`` / ``too_long``
# / ``invalid_url`` had a generic entry, so required-field 422s (type="missing")
# and the siblings below rendered BLANK. All are 3-segment Contract-10 clean.
_NEW_GENERIC_RULES = [
    "missing",
    "string_too_short",
    "string_too_long",
    "int_parsing",
    "float_parsing",
    "string_type",
    "greater_than_equal",
    "less_than_equal",
    "greater_than",
    "less_than",
]


@pytest.mark.parametrize("rule", _NEW_GENERIC_RULES)
def test_new_generic_rule_keys_registered(rule: str) -> None:
    """Each newly-shipped generic-family key is present and non-empty."""
    key = f"validation.generic.{rule}"
    assert key in VALIDATION_MESSAGES
    assert VALIDATION_MESSAGES[key].strip()


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


# ── founder's exact case: required-field 422 no longer renders BLANK ─────────
def test_description_missing_falls_back_to_generic_missing_no_warn(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``resolve('validation.description.missing')`` == generic-missing string.

    This is the founder-reported blank-error bug: a required-field 422 emits
    ``validation.<field>.missing`` (Pydantic type="missing"), which had no
    generic entry and so returned the verbatim id (rendered blank in the UI).
    After the fix it RESOLVES to the generic-missing string — NOT verbatim and
    with ZERO ``i18n.resolver.missing_key`` log records. Mirrors #270.
    """
    per_field_id = "validation.description.missing"
    generic_id = "validation.generic.missing"
    assert per_field_id not in VALIDATION_MESSAGES
    assert generic_id in VALIDATION_MESSAGES

    with caplog.at_level(logging.DEBUG, logger="app.i18n.resolver"):
        result = resolve(per_field_id, locale="en")

    assert result == VALIDATION_MESSAGES[generic_id]
    assert result != per_field_id
    assert not [
        r for r in caplog.records if "i18n.resolver.missing_key" in r.getMessage()
    ]


@pytest.mark.parametrize(
    "field,rule",
    [
        ("description", "missing"),
        ("product_name", "missing"),
        ("price", "greater_than_equal"),
        ("mrp", "less_than_equal"),
        ("brand", "string_too_long"),
        ("title", "string_too_short"),
        ("quantity", "int_parsing"),
        ("weight", "float_parsing"),
        ("color", "string_type"),
        ("stock", "greater_than"),
        ("discount", "less_than"),
    ],
)
def test_new_per_field_rule_resolves_to_its_generic_family(
    field: str, rule: str
) -> None:
    """Each shipped rule maps a dynamic field id to its generic string.

    The bespoke per-field id must NOT exist (so Step-2b is exercised) and the
    resolved string must equal the generic family entry.
    """
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


# ── L_iam_1 RESOLVED: 3-segment auth.token.missing resolves to human copy ────
def test_auth_token_missing_resolves_human_l_iam_1_closed() -> None:
    """``auth.token.missing`` (3-segment) resolves to the human catalog string.

    L_iam_1 is closed: ``core/auth.py`` now raises the 3-segment ids that exist
    in ``messages_en``, so the resolver returns the human copy instead of the
    verbatim id. The legacy 2-segment ``auth.token_missing`` is no longer raised
    anywhere and is intentionally absent from the catalog.
    """
    assert "auth.token.missing" in VALIDATION_MESSAGES
    assert resolve("auth.token.missing") == VALIDATION_MESSAGES["auth.token.missing"]
    # The legacy 2-segment form is gone from the runtime and the catalog.
    assert "auth.token_missing" not in VALIDATION_MESSAGES


# ── existing q.missing key is unchanged (no duplicate, still resolves) ──────
def test_q_missing_still_resolves_unchanged() -> None:
    """``validation.q.missing`` pre-exists; this fix must not disturb it."""
    assert "validation.q.missing" in VALIDATION_MESSAGES
    # It is a real 3-segment key, so it resolves at Step-2 (not via Step-2b).
    assert resolve("validation.q.missing") == VALIDATION_MESSAGES["validation.q.missing"]


# ── bespoke .missing keys still resolve at Step-2 (NOT to the generic) ──────
@pytest.mark.parametrize(
    "bespoke_id",
    [
        "validation.q.missing",
        "catalog.draft.missing",
        # ``pricing.commission.missing`` REMOVED 2026-06-18 (§12.M — commission
        # is now a seller input; the missing-commission failure mode is gone).
        "export.front_image.missing",
        "auth.token.missing",
    ],
)
def test_bespoke_missing_keys_unchanged_resolve_at_step2(bespoke_id: str) -> None:
    """Pre-existing bespoke ``.missing`` keys keep their own copy.

    Adding ``validation.generic.missing`` must not divert these — they are real
    registry keys and resolve at Step-2 to their bespoke string, never to the
    generic-missing fallback.
    """
    assert bespoke_id in VALIDATION_MESSAGES
    resolved = resolve(bespoke_id)
    assert resolved == VALIDATION_MESSAGES[bespoke_id]
    assert resolved != VALIDATION_MESSAGES["validation.generic.missing"]
