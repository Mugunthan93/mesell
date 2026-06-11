"""§5A.C — ``fields[]`` per-field shape conformance + §5A.D/E/F.

Per ``BACKEND_ARCHITECTURE.md`` §5A.C (lines 1559-1589): every entry of
``schema_jsonb.fields[]`` has the 9 locked keys::

    name, canonical_name, marker, data_type, primitive, help_text,
    is_advanced, enum_resolver, validation_message_ids

Plus the locked-value invariants per §5A.D / §5A.E / §5A.F:

  - ``data_type`` ∈ the 8 LOCKED values.
  - ``primitive`` ∈ the 11 LOCKED values.
  - ``enum_resolver`` REQUIRED ``"category"`` or ``"static"`` when
    ``data_type == "dropdown"``, MUST be ``None`` (JSON null) otherwise.
  - ``is_advanced=True`` ONLY when ``canonical_name`` is in the
    ``ADVANCED_CANONICAL_NAMES`` allowlist (V1 locked at ``{"group_id"}``
    per §5A.F + sub-session 2 G1).
  - ``canonical_name`` matches the canonical-name regex (snake_case,
    starts with ``[a-z]``, contains only ``[a-z0-9_]``).
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from app.i18n.advanced_canonical import ADVANCED_CANONICAL_NAMES
from app.i18n.schema_contract import (
    COMPLIANCE_SHAPE_VALUES,
    DATA_TYPE_VALUES,
    ENUM_RESOLVER_VALUES,
    FIELD_SHAPE_KEYS,
    PRIMITIVE_VALUES,
)

pytestmark = pytest.mark.unit

# ----------------------------------------------------------------------------
# Reference fixture — covers compulsory + optional + advanced + each
# data_type variant the test asserts against.
# ----------------------------------------------------------------------------
_REFERENCE_FIELDS: list[dict[str, Any]] = [
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
    },
    {
        "name": "Brand",
        "canonical_name": "brand",
        "marker": "compulsory",
        "data_type": "dropdown",
        "primitive": "dropdown_api_search",
        "help_text": "Pick your brand from the list.",
        "is_advanced": False,
        "enum_resolver": "category",
        "validation_message_ids": [],
    },
    {
        "name": "Country of Origin",
        "canonical_name": "country_of_origin",
        "marker": "compulsory",
        "data_type": "dropdown",
        "primitive": "dropdown_small",
        "help_text": "Where the product was made.",
        "is_advanced": False,
        "enum_resolver": "static",
        "validation_message_ids": [],
        # `enum_values` allowed per §5A.E forward-compat; not in locked keys.
        "enum_values": ["India", "China", "USA", "UK", "Japan"],
    },
    {
        "name": "Group ID",
        "canonical_name": "group_id",
        "marker": "optional",
        "data_type": "text",
        "primitive": "text_short",
        "help_text": "Advanced — link product variants together.",
        "is_advanced": True,
        "enum_resolver": None,
        "validation_message_ids": [],
    },
    {
        "name": "MRP",
        "canonical_name": "mrp",
        "marker": "compulsory",
        "data_type": "currency",
        "primitive": "currency",
        "help_text": "Maximum Retail Price in rupees.",
        "is_advanced": False,
        "enum_resolver": None,
        "validation_message_ids": [],
    },
    {
        "name": "Product Image 1",
        "canonical_name": "image_1",
        "marker": "compulsory",
        "data_type": "image",
        "primitive": "image_upload",
        "help_text": "Front-of-product photo.",
        "is_advanced": False,
        "enum_resolver": None,
        "validation_message_ids": [],
    },
]


_CANONICAL_NAME_REGEX = re.compile(r"^[a-z][a-z0-9_]*$")


def test_every_field_has_locked_nine_keys() -> None:
    """§5A.C — each fields[] entry carries the 9 locked keys.

    Extra keys per the §5A.C forward-compat note (e.g. ``unit_suffix``,
    ``enum_values``) are permitted — we assert the 9 are a SUBSET, not
    that they are the ONLY keys.
    """
    assert len(FIELD_SHAPE_KEYS) == 9
    for i, field in enumerate(_REFERENCE_FIELDS):
        present = set(field.keys())
        missing = FIELD_SHAPE_KEYS - present
        assert not missing, (
            f"fields[{i}] (canonical_name={field.get('canonical_name')!r}) "
            f"missing keys: {sorted(missing)}"
        )


@pytest.mark.parametrize("field_idx", range(len(_REFERENCE_FIELDS)))
def test_data_type_in_locked_set(field_idx: int) -> None:
    """§5A.C — data_type ∈ 8 locked values."""
    assert _REFERENCE_FIELDS[field_idx]["data_type"] in DATA_TYPE_VALUES


@pytest.mark.parametrize("field_idx", range(len(_REFERENCE_FIELDS)))
def test_primitive_in_locked_set(field_idx: int) -> None:
    """§5A.D — primitive ∈ 11 locked values."""
    assert _REFERENCE_FIELDS[field_idx]["primitive"] in PRIMITIVE_VALUES


@pytest.mark.parametrize("field_idx", range(len(_REFERENCE_FIELDS)))
def test_enum_resolver_invariant(field_idx: int) -> None:
    """§5A.E — REQUIRED when data_type=='dropdown', MUST be None otherwise."""
    f = _REFERENCE_FIELDS[field_idx]
    if f["data_type"] == "dropdown":
        assert f["enum_resolver"] in ("category", "static"), (
            f"dropdown field {f['canonical_name']!r} has enum_resolver="
            f"{f['enum_resolver']!r}; §5A.E requires 'category' or 'static'."
        )
    else:
        assert f["enum_resolver"] is None, (
            f"non-dropdown field {f['canonical_name']!r} has enum_resolver="
            f"{f['enum_resolver']!r}; §5A.E locks it to None."
        )
    assert f["enum_resolver"] in ENUM_RESOLVER_VALUES


@pytest.mark.parametrize("field_idx", range(len(_REFERENCE_FIELDS)))
def test_marker_is_binary(field_idx: int) -> None:
    """§5A.C — marker ∈ {"compulsory", "optional"} (binary tiering)."""
    assert _REFERENCE_FIELDS[field_idx]["marker"] in ("compulsory", "optional")


@pytest.mark.parametrize("field_idx", range(len(_REFERENCE_FIELDS)))
def test_canonical_name_regex(field_idx: int) -> None:
    """§5A.C — canonical_name is snake_case ([a-z][a-z0-9_]*)."""
    cn = _REFERENCE_FIELDS[field_idx]["canonical_name"]
    assert _CANONICAL_NAME_REGEX.match(cn), (
        f"canonical_name {cn!r} does not match ^[a-z][a-z0-9_]*$ per §5A.C."
    )


@pytest.mark.parametrize("field_idx", range(len(_REFERENCE_FIELDS)))
def test_help_text_non_empty(field_idx: int) -> None:
    """§5A.C / §0.H F5 — every field carries help_text (no empty allowed)."""
    f = _REFERENCE_FIELDS[field_idx]
    assert isinstance(f["help_text"], str)
    assert f["help_text"].strip(), (
        f"field {f['canonical_name']!r} has empty help_text; §5A.C forbids."
    )


@pytest.mark.parametrize("field_idx", range(len(_REFERENCE_FIELDS)))
def test_validation_message_ids_is_a_list_of_strs(field_idx: int) -> None:
    """§5A.C — validation_message_ids is a (possibly empty) list[str]."""
    vmids = _REFERENCE_FIELDS[field_idx]["validation_message_ids"]
    assert isinstance(vmids, list)
    for v in vmids:
        assert isinstance(v, str) and v.strip()


@pytest.mark.parametrize("field_idx", range(len(_REFERENCE_FIELDS)))
def test_is_advanced_allowlist(field_idx: int) -> None:
    """§5A.F — is_advanced=True ONLY for canonical_name ∈ allowlist."""
    f = _REFERENCE_FIELDS[field_idx]
    if f["is_advanced"]:
        assert f["canonical_name"] in ADVANCED_CANONICAL_NAMES, (
            f"field {f['canonical_name']!r} has is_advanced=True but is not "
            f"in ADVANCED_CANONICAL_NAMES={set(ADVANCED_CANONICAL_NAMES)} "
            f"— §5A.F amendment required to widen."
        )


def test_advanced_canonical_names_is_exactly_one_element() -> None:
    """§5A.F + sub-session 2 G1 — V1 allowlist locked at exactly 1 element."""
    assert ADVANCED_CANONICAL_NAMES == frozenset({"group_id"})
    assert len(ADVANCED_CANONICAL_NAMES) == 1


def test_data_type_values_set_has_exactly_eight_members() -> None:
    """§5A.C — locked enum of 8 data_type values."""
    assert len(DATA_TYPE_VALUES) == 8


def test_primitive_values_set_has_exactly_eleven_members() -> None:
    """§5A.D — locked set of 11 input primitives."""
    assert len(PRIMITIVE_VALUES) == 11


def test_compliance_shape_values_set_has_exactly_two_members() -> None:
    """§5A.B / §5A.F — locked at standard / collapsed."""
    assert len(COMPLIANCE_SHAPE_VALUES) == 2


def test_enum_resolver_values_set_has_exactly_three_members() -> None:
    """§5A.E — category / static / None."""
    assert len(ENUM_RESOLVER_VALUES) == 3
    assert ENUM_RESOLVER_VALUES == frozenset({"category", "static", None})
