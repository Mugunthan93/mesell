"""§5A.B — ``templates.schema_jsonb`` top-level envelope shape conformance.

Per ``BACKEND_ARCHITECTURE.md`` §5A.B (lines 1529-1555): every envelope
carries 7 locked top-level keys::

    fields, compulsory_count, optional_count, total_count,
    wizard_step_count, main_sheet_label, compliance_shape

This test asserts envelope conformance against a representative fixture.
The fixture is the canonical example from §5A.B lines 1533-1543 plus a
single field (so ``fields[]`` is non-empty). Real seed-time envelopes
ship via ``scripts/build_template_schemas.py``; the §19 seed-time
validator is the production check — this test guards the consumption
contract that ``category`` / ``catalog`` / ``export`` modules rely on.

Also asserts:
  - ``total_count == compulsory_count + optional_count`` (seed-time
    invariant per §5A.B).
  - ``compliance_shape`` ∈ ``{"standard", "collapsed"}`` (§5A.F).
  - Per-key type-shape conformance for the count fields (``int``) and
    label fields (``str``).
"""

from __future__ import annotations

from typing import Any

import pytest

from app.i18n.schema_contract import (
    COMPLIANCE_SHAPE_VALUES,
    ENVELOPE_KEYS,
)

# ----------------------------------------------------------------------------
# Reference fixture — verbatim from §5A.B example envelope plus one field.
# ----------------------------------------------------------------------------
_REFERENCE_ENVELOPE: dict[str, Any] = {
    "fields": [
        {
            "name": "Product Name",
            "canonical_name": "product_name",
            "marker": "compulsory",
            "data_type": "text",
            "primitive": "text_short",
            "help_text": "Please enter the product name.",
            "is_advanced": False,
            "enum_resolver": None,
            "validation_message_ids": [
                "validation.product_name.too_short",
                "validation.product_name.no_special_chars",
            ],
        }
    ],
    "compulsory_count": 28,
    "optional_count": 14,
    "total_count": 42,
    "wizard_step_count": 6,
    "main_sheet_label": "Sarees-Fill this",
    "compliance_shape": "standard",
}


def test_envelope_has_exactly_seven_top_level_keys() -> None:
    """§5A.B lock — no extra top-level keys permitted in V1."""
    assert set(_REFERENCE_ENVELOPE.keys()) == ENVELOPE_KEYS
    assert len(ENVELOPE_KEYS) == 7


@pytest.mark.parametrize("key", sorted(ENVELOPE_KEYS))
def test_envelope_required_key_present(key: str) -> None:
    """Every locked envelope key must be present — REQUIRED per §5A.B."""
    assert key in _REFERENCE_ENVELOPE


def test_envelope_fields_is_a_list() -> None:
    """`fields: list[FieldSpec]` per §5A.B."""
    assert isinstance(_REFERENCE_ENVELOPE["fields"], list)


def test_envelope_count_fields_are_ints() -> None:
    """`compulsory_count`, `optional_count`, `total_count`, `wizard_step_count` are ints."""
    for key in (
        "compulsory_count",
        "optional_count",
        "total_count",
        "wizard_step_count",
    ):
        assert isinstance(_REFERENCE_ENVELOPE[key], int)


def test_envelope_label_fields_are_strs() -> None:
    """`main_sheet_label` and `compliance_shape` are strs."""
    assert isinstance(_REFERENCE_ENVELOPE["main_sheet_label"], str)
    assert isinstance(_REFERENCE_ENVELOPE["compliance_shape"], str)


def test_envelope_total_count_invariant() -> None:
    """§5A.B invariant: total_count == compulsory_count + optional_count."""
    assert (
        _REFERENCE_ENVELOPE["total_count"]
        == _REFERENCE_ENVELOPE["compulsory_count"] + _REFERENCE_ENVELOPE["optional_count"]
    )


def test_envelope_compliance_shape_in_locked_set() -> None:
    """§5A.F — compliance_shape ∈ {"standard", "collapsed"}."""
    assert _REFERENCE_ENVELOPE["compliance_shape"] in COMPLIANCE_SHAPE_VALUES
    assert COMPLIANCE_SHAPE_VALUES == {"standard", "collapsed"}


def test_envelope_wizard_step_count_in_range() -> None:
    """§5A.B — wizard_step_count is clamped to [3, 8]."""
    assert 3 <= _REFERENCE_ENVELOPE["wizard_step_count"] <= 8
