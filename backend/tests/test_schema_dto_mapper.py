"""§5A.C read-time DTO mapper conformance (catalog-form-fix 2026-06-16).

Exercises ``category.service._map_field_to_dto`` /
``_map_envelope_to_dto`` — the pure projection that materialises the FLAT
§5A.C 9-key WIRE shape at read time from the RICH at-rest §5.6.1 envelope
served by ``fetch_schema``.

The mapper is the fix for the catalog-form UI bugs:
  - #1/#3 blank labels / "undefined" → the rich shape carried no ``name`` /
    ``help_text``; the mapper derives non-empty values for both.
  - #2 dead dropdowns → the rich shape carried no ``enum_resolver``; the
    mapper derives ``"category"`` for every V1 dropdown so the FE lazy-loads
    enums and ``catalog.validate_product`` resolves them.

Rich fixtures here are constructed to EXACTLY mirror the key set produced by
``scripts/build_template_schemas.py:build_field_schema`` (the seed-time
source-of-truth writer): the 25 §5.6.1 keys

    canonical_name, data_type, primitive, marker, is_advanced, is_hidden,
    compliance_role, step_id, max_length, min_length, regex, min_value,
    max_value, unit_suffix, display_label, display_help, display_placeholder,
    display_unit_label, validation_message, help_url, meesho_column_header,
    meesho_column_index, meesho_default, enum_codes_map, enum_labels

— and CRITICALLY include the ``display_help=None`` case (a seed field with no
help text) to exercise the ``help_text`` fallback.  ``build_field_schema``
emits NO ``name`` / ``help_text`` / ``enum_resolver`` / ``validation_message_ids``
keys — that absence is exactly what the mapper repairs.

We deliberately do NOT import the script module: it imports
``app.shared.config.settings`` and mutates ``sys.path`` at import time, which
couples a pure-unit test to runtime env config.  The §5A.C spec permits this
mirror-fixture approach.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.i18n.schema_contract import (
    DATA_TYPE_VALUES,
    FIELD_SHAPE_KEYS,
    PRIMITIVE_VALUES,
)
from app.modules.category.service import (
    _map_envelope_to_dto,
    _map_field_to_dto,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Rich §5.6.1 fixtures — mirror build_field_schema's exact 25-key output.
# ---------------------------------------------------------------------------
def _rich_field(
    *,
    canonical_name: str,
    data_type: str = "text",
    primitive: str = "text_short",
    marker: str = "optional",
    is_advanced: bool = False,
    display_label: dict[str, str] | None = None,
    display_help: dict[str, str] | None = None,
    enum_codes_map: dict[str, Any] | None = None,
    meesho_column_index: int = 0,
) -> dict[str, Any]:
    """Build a rich field dict with build_field_schema's EXACT key set.

    ``display_label`` defaults to the title-cased canonical_name (matching
    the builder's else-branch).  Pass ``display_label=None`` explicitly only
    to exercise the name fallback edge case (rich shape with missing label).
    """
    return {
        # Canonical layer
        "canonical_name": canonical_name,
        "data_type": data_type,
        "primitive": primitive,
        "marker": marker,
        "is_advanced": is_advanced,
        "is_hidden": False,
        "compliance_role": None,
        "step_id": "essentials",
        "max_length": None,
        "min_length": None,
        "regex": None,
        "min_value": None,
        "max_value": None,
        "unit_suffix": None,
        # Display layer
        "display_label": display_label,
        "display_help": display_help,
        "display_placeholder": None,
        "display_unit_label": None,
        "validation_message": None,
        "help_url": None,
        # Export layer
        "meesho_column_header": canonical_name,
        "meesho_column_index": meesho_column_index,
        "meesho_default": None,
        # Enum
        "enum_codes_map": enum_codes_map,
        "enum_labels": None,
    }


# A compulsory text field WITH a label but display_help=None (seed had no
# help) → exercises the help_text fallback.
RICH_TEXT_NO_HELP = _rich_field(
    canonical_name="product_name",
    data_type="text",
    primitive="text_short",
    marker="compulsory",
    display_label={"en": "Product Name"},
    display_help=None,
)

# A dropdown with no inline enum_codes_map → enum_resolver must be "category".
RICH_DROPDOWN_CATEGORY = _rich_field(
    canonical_name="colour",
    data_type="dropdown",
    primitive="dropdown_medium",
    marker="compulsory",
    display_label={"en": "Colour"},
    display_help={"en": "Pick the main colour."},
    enum_codes_map=None,
)

# An advanced group field (the V1 ADVANCED allowlist member).
RICH_ADVANCED = _rich_field(
    canonical_name="group_id",
    data_type="text",
    primitive="text_short",
    marker="optional",
    is_advanced=True,
    display_label={"en": "Group Id"},
    display_help={"en": "Variation group identifier."},
)

# A currency field.
RICH_CURRENCY = _rich_field(
    canonical_name="mrp",
    data_type="currency",
    primitive="currency",
    marker="compulsory",
    display_label={"en": "MRP"},
    display_help={"en": "Maximum retail price."},
)

# An image field.
RICH_IMAGE = _rich_field(
    canonical_name="main_image",
    data_type="image",
    primitive="image_upload",
    marker="compulsory",
    display_label={"en": "Main Image"},
    display_help={"en": "Upload the main product image."},
)

# Edge: rich field with MISSING display_label entirely → name fallback.
RICH_NO_LABEL = _rich_field(
    canonical_name="net_quantity",
    data_type="text",
    primitive="text_short",
    marker="optional",
    display_label=None,
    display_help=None,
)

ALL_RICH = [
    RICH_TEXT_NO_HELP,
    RICH_DROPDOWN_CATEGORY,
    RICH_ADVANCED,
    RICH_CURRENCY,
    RICH_IMAGE,
    RICH_NO_LABEL,
]


# ---------------------------------------------------------------------------
# Per-field DTO conformance
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("rich", ALL_RICH)
def test_dto_has_exactly_the_nine_locked_keys(rich: dict[str, Any]) -> None:
    dto = _map_field_to_dto(rich)
    # All 9 §5A.C keys present.
    assert FIELD_SHAPE_KEYS.issubset(dto.keys())
    # No rich-only keys leak through (only the 9 + conditional enum_values).
    allowed = FIELD_SHAPE_KEYS | {"enum_values"}
    assert set(dto.keys()).issubset(allowed)
    for leaked in (
        "is_hidden",
        "compliance_role",
        "step_id",
        "meesho_column_header",
        "meesho_column_index",
        "display_label",
        "display_help",
        "enum_codes_map",
        "enum_labels",
        "validation_message",
    ):
        assert leaked not in dto


@pytest.mark.parametrize("rich", ALL_RICH)
def test_name_is_non_empty_str(rich: dict[str, Any]) -> None:
    dto = _map_field_to_dto(rich)
    assert isinstance(dto["name"], str)
    assert dto["name"] != ""


@pytest.mark.parametrize("rich", ALL_RICH)
def test_help_text_is_non_empty_str(rich: dict[str, Any]) -> None:
    dto = _map_field_to_dto(rich)
    assert isinstance(dto["help_text"], str)
    assert dto["help_text"] != ""


@pytest.mark.parametrize("rich", ALL_RICH)
def test_data_type_and_primitive_in_locked_sets(rich: dict[str, Any]) -> None:
    dto = _map_field_to_dto(rich)
    assert dto["data_type"] in DATA_TYPE_VALUES
    assert dto["primitive"] in PRIMITIVE_VALUES


@pytest.mark.parametrize("rich", ALL_RICH)
def test_validation_message_ids_is_empty_list(rich: dict[str, Any]) -> None:
    dto = _map_field_to_dto(rich)
    assert isinstance(dto["validation_message_ids"], list)
    assert dto["validation_message_ids"] == []


@pytest.mark.parametrize("rich", ALL_RICH)
def test_enum_resolver_invariant(rich: dict[str, Any]) -> None:
    dto = _map_field_to_dto(rich)
    if dto["data_type"] == "dropdown":
        assert dto["enum_resolver"] in ("category", "static")
    else:
        assert dto["enum_resolver"] is None


@pytest.mark.parametrize("rich", ALL_RICH)
def test_enum_values_only_when_static(rich: dict[str, Any]) -> None:
    dto = _map_field_to_dto(rich)
    if dto.get("enum_resolver") == "static":
        assert "enum_values" in dto
    else:
        assert "enum_values" not in dto


# ---------------------------------------------------------------------------
# Targeted derivations
# ---------------------------------------------------------------------------
def test_dropdown_no_inline_map_derives_category() -> None:
    dto = _map_field_to_dto(RICH_DROPDOWN_CATEGORY)
    assert dto["enum_resolver"] == "category"
    assert "enum_values" not in dto


def test_dropdown_with_inline_map_derives_static_and_surfaces_values() -> None:
    rich = _rich_field(
        canonical_name="size",
        data_type="dropdown",
        primitive="dropdown_small",
        marker="compulsory",
        display_label={"en": "Size"},
        display_help={"en": "Pick a size."},
        enum_codes_map={"S": {"meesho": "S"}, "M": {"meesho": "M"}},
    )
    dto = _map_field_to_dto(rich)
    assert dto["enum_resolver"] == "static"
    assert dto["enum_values"] == ["S", "M"]


def test_help_text_fallback_when_display_help_none() -> None:
    dto = _map_field_to_dto(RICH_TEXT_NO_HELP)
    # display_help was None → fallback "Enter {name}." → non-empty.
    assert dto["help_text"] == "Enter Product Name."


def test_name_fallback_when_display_label_missing() -> None:
    dto = _map_field_to_dto(RICH_NO_LABEL)
    # display_label None → title-cased canonical_name.
    assert dto["name"] == "Net Quantity"
    assert dto["name"] != ""


def test_passthrough_fields_unchanged() -> None:
    dto = _map_field_to_dto(RICH_ADVANCED)
    assert dto["canonical_name"] == "group_id"
    assert dto["marker"] == "optional"
    assert dto["is_advanced"] is True
    assert dto["data_type"] == "text"
    assert dto["primitive"] == "text_short"


# ---------------------------------------------------------------------------
# Envelope projection
# ---------------------------------------------------------------------------
def _rich_envelope() -> dict[str, Any]:
    return {
        "fields": [dict(f) for f in ALL_RICH],
        "compulsory_count": 4,
        "optional_count": 2,
        "total_count": 6,
        "wizard_step_count": 3,
        "main_sheet_label": "Products",
        "compliance_shape": "standard",
    }


def test_envelope_passthrough_keys_survive_unchanged() -> None:
    env = _rich_envelope()
    out = _map_envelope_to_dto(env)
    assert out["compulsory_count"] == 4
    assert out["optional_count"] == 2
    assert out["total_count"] == 6
    assert out["wizard_step_count"] == 3
    assert out["main_sheet_label"] == "Products"
    assert out["compliance_shape"] == "standard"


def test_envelope_field_count_unchanged_and_counts_not_mutated() -> None:
    env = _rich_envelope()
    out = _map_envelope_to_dto(env)
    assert len(out["fields"]) == len(ALL_RICH)
    # Counts are NOT recomputed from the mapped fields.
    assert out["total_count"] == 6


def test_envelope_fields_are_all_dto_shape() -> None:
    out = _map_envelope_to_dto(_rich_envelope())
    for dto in out["fields"]:
        assert FIELD_SHAPE_KEYS.issubset(dto.keys())
        assert isinstance(dto["name"], str) and dto["name"] != ""
        assert isinstance(dto["help_text"], str) and dto["help_text"] != ""
