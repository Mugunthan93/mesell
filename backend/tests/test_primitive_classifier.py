"""Regression tests for backend/app/i18n/primitive_classifier.py.

These tests PIN the primitive inference rules.  Any future edit to
UNIT_KEYWORDS, CURRENCY_PATTERNS, LONG_PATTERNS, or the ``classify_primitive``
function that changes the output for ANY of these tuples will fail here,
surfacing drift in CI immediately before re-seeding.

The test coverage targets all 10 primitive values:
  text_short, text_long, currency,
  number, number_with_unit,
  dropdown_small, dropdown_medium, dropdown_large, dropdown_api_search,
  image_upload.

Note: ``address_group`` is NOT a catalog primitive and is never emitted.  See
§4.1 note and ``primitive_classifier.py`` module docstring.
"""

from __future__ import annotations

import pytest

from app.i18n.primitive_classifier import (
    CLASSIFIER_VERSION,
    CURRENCY_PATTERNS,
    LONG_PATTERNS,
    UNIT_KEYWORDS,
    classify_primitive,
)


# ---------------------------------------------------------------------------
# Smoke tests — module-level properties
# ---------------------------------------------------------------------------


def test_classifier_version_is_v1() -> None:
    """CLASSIFIER_VERSION must be 'v1' until explicitly bumped."""
    assert CLASSIFIER_VERSION == "v1"


def test_unit_keywords_not_empty() -> None:
    """UNIT_KEYWORDS constant must have at least 5 entries."""
    assert len(UNIT_KEYWORDS) >= 5


def test_currency_patterns_not_empty() -> None:
    """CURRENCY_PATTERNS constant must include 'price' and 'mrp'."""
    assert "price" in CURRENCY_PATTERNS
    assert "mrp" in CURRENCY_PATTERNS


def test_long_patterns_includes_address() -> None:
    """LONG_PATTERNS must include 'address' (drives text_long for address fields)."""
    assert "address" in LONG_PATTERNS


# ---------------------------------------------------------------------------
# Parametrised regression suite — 15 canonical tuples
# Format: (name, data_type, enum_count, has_unit_companion, expected_primitive)
# ---------------------------------------------------------------------------

REGRESSION_CASES: list[tuple[str, str, int | None, bool, str]] = [
    # text_short
    ("Product Name", "text", None, False, "text_short"),
    # text_long — matches *description
    ("Product Description", "text", None, False, "text_long"),
    # text_long — matches *address pattern
    ("Manufacturer Address", "text", None, False, "text_long"),
    # number (plain — no unit keyword, no companion)
    ("Inventory", "number", None, False, "number"),
    # number_with_unit — has_unit_companion=True overrides name check
    ("Net Weight (gms)", "number", None, True, "number_with_unit"),
    # number_with_unit — name matches UNIT_KEYWORDS ("voltage")
    ("Voltage", "number", None, False, "number_with_unit"),
    # currency — name matches *price
    ("Meesho Price", "text", None, False, "currency"),
    # currency — name matches mrp exactly
    ("MRP", "text", None, False, "currency"),
    # dropdown_small (enum_count=2)
    ("Veg/NonVeg", "dropdown", 2, False, "dropdown_small"),
    # dropdown_medium (enum_count=50)
    ("Fabric", "dropdown", 50, False, "dropdown_medium"),
    # dropdown_large (enum_count=321)
    ("Length Size", "dropdown", 321, False, "dropdown_large"),
    # dropdown_api_search (enum_count=3998)
    ("Brand", "dropdown", 3998, False, "dropdown_api_search"),
    # dropdown_api_search (enum_count=4481 — Compatible Models, max in corpus)
    ("Compatible Models", "dropdown", 4481, False, "dropdown_api_search"),
    # image_upload
    ("Image 1", "image_url", None, False, "image_upload"),
    # image_upload (confirming all image_url → image_upload regardless of name)
    ("Image 2", "image_url", None, False, "image_upload"),
]


@pytest.mark.parametrize(
    "name, data_type, enum_count, has_unit_companion, expected",
    REGRESSION_CASES,
    ids=[case[0] for case in REGRESSION_CASES],
)
def test_classify_primitive_regression(
    name: str,
    data_type: str,
    enum_count: int | None,
    has_unit_companion: bool,
    expected: str,
) -> None:
    """``classify_primitive`` must produce the expected primitive for every pinned tuple."""
    result = classify_primitive(
        name=name,
        data_type=data_type,
        enum_count=enum_count,
        has_unit_companion=has_unit_companion,
    )
    assert result == expected, (
        f"classify_primitive({name!r}, {data_type!r}, enum_count={enum_count}, "
        f"has_unit_companion={has_unit_companion}) returned {result!r}, expected {expected!r}. "
        f"If this was intentional, bump CLASSIFIER_VERSION and re-seed."
    )


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------


def test_unknown_data_type_falls_back_to_text_short() -> None:
    """Unrecognised data_type strings must fall back to text_short."""
    result = classify_primitive("some_field", "boolean", None, False)
    assert result == "text_short"


def test_dropdown_enum_count_boundary_20() -> None:
    """enum_count exactly 20 → dropdown_small (boundary inclusive)."""
    assert classify_primitive("color", "dropdown", 20, False) == "dropdown_small"


def test_dropdown_enum_count_boundary_21() -> None:
    """enum_count exactly 21 → dropdown_medium."""
    assert classify_primitive("color", "dropdown", 21, False) == "dropdown_medium"


def test_dropdown_enum_count_boundary_100() -> None:
    """enum_count exactly 100 → dropdown_medium (boundary inclusive)."""
    assert classify_primitive("size", "dropdown", 100, False) == "dropdown_medium"


def test_dropdown_enum_count_boundary_101() -> None:
    """enum_count exactly 101 → dropdown_large."""
    assert classify_primitive("size", "dropdown", 101, False) == "dropdown_large"


def test_dropdown_enum_count_boundary_500() -> None:
    """enum_count exactly 500 → dropdown_large (boundary inclusive)."""
    assert classify_primitive("fabric", "dropdown", 500, False) == "dropdown_large"


def test_dropdown_enum_count_boundary_501() -> None:
    """enum_count exactly 501 → dropdown_api_search."""
    assert classify_primitive("fabric", "dropdown", 501, False) == "dropdown_api_search"


def test_dropdown_none_enum_count_treated_as_zero() -> None:
    """None enum_count for dropdown → treated as 0 → dropdown_small."""
    assert classify_primitive("status", "dropdown", None, False) == "dropdown_small"


def test_number_with_unit_from_keyword_weight() -> None:
    """'weight' in field name → number_with_unit."""
    assert classify_primitive("net_weight_grams", "number", None, False) == "number_with_unit"


def test_number_with_unit_overrides_when_companion_flag_set() -> None:
    """has_unit_companion=True → number_with_unit even if name has no unit keyword."""
    assert classify_primitive("quantity", "number", None, True) == "number_with_unit"


def test_currency_mrp_case_insensitive_name() -> None:
    """'mrp' substring anywhere in lowercased name → currency."""
    assert classify_primitive("mrp_before_discount", "text", None, False) == "currency"


def test_text_long_from_ingredients() -> None:
    """Field name containing 'ingredients' → text_long."""
    assert classify_primitive("ingredients", "text", None, False) == "text_long"


def test_text_long_from_key_features() -> None:
    """Field name containing 'key_features' → text_long."""
    assert classify_primitive("key_features", "text", None, False) == "text_long"


def test_ten_primitive_vocabulary_only() -> None:
    """Verify all 10 primitives are reachable and no 11th is ever returned."""
    valid_primitives = {
        "text_short", "text_long", "currency",
        "number", "number_with_unit",
        "dropdown_small", "dropdown_medium", "dropdown_large", "dropdown_api_search",
        "image_upload",
    }
    test_inputs = [
        ("x", "text", None, False),
        ("product_description", "text", None, False),
        ("meesho_price", "text", None, False),
        ("qty", "number", None, False),
        ("net_weight", "number", None, False),
        ("color", "dropdown", 5, False),
        ("fabric", "dropdown", 50, False),
        ("size", "dropdown", 200, False),
        ("brand", "dropdown", 3000, False),
        ("image_1_url", "image_url", None, False),
        ("unknown_type", "boolean", None, False),  # fallback
    ]
    for name, dtype, ec, huc in test_inputs:
        result = classify_primitive(name, dtype, ec, huc)
        assert result in valid_primitives, (
            f"classify_primitive({name!r}) returned unexpected primitive {result!r}"
        )
