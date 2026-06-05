"""Primitive classifier — canonical code lock for ``templates.schema_jsonb.fields[*].primitive``.

Source: §4.1 + §5.6.5 of ``docs/MVP_ARCHITECTURE.md`` (prose table).
This file IS the source of truth for primitive inference.  The doc references
this module.  Do NOT edit the constants here without:
  1. Bumping ``CLASSIFIER_VERSION``.
  2. Re-running ``scripts/seed_all.py`` against dev and verifying that
     ``templates.schema_jsonb`` primitive values are unchanged (or intentionally
     updated and reviewed with the founder).
  3. Confirming ``backend/tests/test_primitive_classifier.py`` all pass.

Any quarterly Meesho refresh that introduces new field patterns affecting
primitive assignment must go through this file.

The 10-element primitive vocabulary (``address_group`` is NOT a catalog
primitive — see §4.1 note):

  image_upload        data_type == image_url
  currency            data_type == text, name matches *price | mrp | *returns_price
  text_long           data_type == text, name matches long-text patterns
  text_short          data_type == text (fallback)
  number_with_unit    data_type == number, name matches unit keywords OR has_unit_companion
  number              data_type == number (fallback)
  dropdown_small      data_type == dropdown, enum_count 1-20
  dropdown_medium     data_type == dropdown, enum_count 21-100
  dropdown_large      data_type == dropdown, enum_count 101-500
  dropdown_api_search data_type == dropdown, enum_count >500

Usage::

    from app.i18n.primitive_classifier import classify_primitive, CLASSIFIER_VERSION
"""

from __future__ import annotations

# Bump this whenever the constants or logic change.
CLASSIFIER_VERSION = "v1"

# ---------------------------------------------------------------------------
# Constants — substring patterns matched against the lowercased canonical name.
# ---------------------------------------------------------------------------

UNIT_KEYWORDS: tuple[str, ...] = (
    "weight",
    "voltage",
    "wattage",
    "frequency",
    "capacity",
    "length",
    "width",
    "height",
    "breadth",
)

CURRENCY_PATTERNS: tuple[str, ...] = (
    "price",
    "mrp",
    "returns_price",
    "defective_returns",
)

LONG_PATTERNS: tuple[str, ...] = (
    "description",
    "notes",
    "ingredients",
    "details",
    "address",
    "active_ingredients",
    "key_features",
)


def classify_primitive(
    name: str,
    data_type: str,
    enum_count: int | None,
    has_unit_companion: bool,
) -> str:
    """Infer the frontend input primitive for a catalog field.

    Implements the classification table from §4.1 of ``docs/MVP_ARCHITECTURE.md``.

    Args:
        name: The *canonical* field name (snake_case), e.g. ``"net_weight_grams"``.
              Used for substring pattern matching.
        data_type: Raw Meesho data type string: one of ``"text"``, ``"number"``,
                   ``"dropdown"``, ``"image_url"``.
        enum_count: Number of enum values for dropdown fields, or ``None``.
                    Treated as 0 when ``None``.
        has_unit_companion: ``True`` when the batch JSON indicates the field has
                            an associated ``_unit`` companion field in the same
                            leaf.  Forces ``number_with_unit`` even when the
                            field name does not match ``UNIT_KEYWORDS``.

    Returns:
        One of the 10 primitive strings.  ``"text_short"`` is the final fallback.

    Note on ``address_group``:
        ``address_group`` is a *seller-profile onboarding* composite, not a
        catalog-wizard primitive.  It never appears in
        ``templates.schema_jsonb.fields[*].primitive``.  See §4.1 note.
    """
    cn = name.lower()
    safe_enum_count = enum_count or 0

    # image_url → image_upload (always, regardless of name)
    if data_type == "image_url":
        return "image_upload"

    # dropdown → bucket by enum_count
    if data_type == "dropdown":
        if safe_enum_count <= 20:
            return "dropdown_small"
        if safe_enum_count <= 100:
            return "dropdown_medium"
        if safe_enum_count <= 500:
            return "dropdown_large"
        return "dropdown_api_search"

    # number → unit check first
    if data_type == "number":
        if has_unit_companion or any(kw in cn for kw in UNIT_KEYWORDS):
            return "number_with_unit"
        return "number"

    # text → currency > long-text > short-text
    if data_type == "text":
        if any(p in cn for p in CURRENCY_PATTERNS):
            return "currency"
        if any(p in cn for p in LONG_PATTERNS):
            return "text_long"
        return "text_short"

    # Fallback for any unrecognised data_type
    return "text_short"
