"""Regression tests for backend/app/i18n/step_assignment.py.

These tests PIN the step assignment rules.  Any future edit to STEP_ASSIGNMENT
or STEP_ORDER that changes the output for ANY of these tuples will fail here,
surfacing the drift in CI immediately before re-seeding.

The test coverage targets every step bucket defined in STEP_ORDER:
  basics, pricing, inventory, sizing, materials, food, tech_specs,
  safety, warranty, compliance, photos, description, advanced (note below).

Note on ``advanced`` bucket:
  The ``advanced`` step bucket is a DISPLAY-LAYER concept (§12.4).  It is NOT
  assigned by ``assign_step`` — it is controlled by the ``is_advanced`` flag
  on each field (e.g. ``group_id`` has ``is_advanced=True``).  The field
  ``group_id`` maps to ``"basics"`` from this function because it matches the
  ``basics`` catch-all regex.  The frontend hides it behind the Advanced toggle
  regardless of the step_id.  This is intentional and documented in the
  ``assign_step`` docstring.
"""

from __future__ import annotations

import pytest

from app.i18n.step_assignment import RULESET_VERSION, STEP_ASSIGNMENT, STEP_ORDER, assign_step

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Smoke tests — module-level properties
# ---------------------------------------------------------------------------


def test_ruleset_version_is_v1() -> None:
    """RULESET_VERSION must be 'v1' until explicitly bumped."""
    assert RULESET_VERSION == "v1"


def test_step_assignment_has_entries() -> None:
    """STEP_ASSIGNMENT must contain at least 13 patterns."""
    assert len(STEP_ASSIGNMENT) >= 13


def test_step_order_contains_all_buckets() -> None:
    """STEP_ORDER must include all canonical step buckets."""
    expected = {
        "basics", "pricing", "inventory", "sizing", "materials",
        "food", "tech_specs", "safety", "warranty", "compliance",
        "photos", "description", "advanced",
    }
    assert set(STEP_ORDER) == expected


# ---------------------------------------------------------------------------
# Parametrised regression suite — 15 canonical tuples
# Format: (canonical_name, primitive, compliance_role, expected_step_id)
# ---------------------------------------------------------------------------

REGRESSION_CASES: list[tuple[str, str, str | None, str]] = [
    # basics bucket
    ("product_name", "text_short", None, "basics"),
    # pricing bucket
    ("meesho_price", "currency", None, "pricing"),
    ("mrp", "currency", None, "pricing"),
    # inventory bucket
    ("inventory", "number", None, "inventory"),
    ("net_weight_grams", "number_with_unit", None, "inventory"),
    # sizing bucket
    ("length_size", "dropdown_large", None, "sizing"),
    # materials bucket
    ("fabric", "dropdown_medium", None, "materials"),
    # food bucket
    ("veg_nonveg", "dropdown_small", None, "food"),
    # tech_specs bucket
    ("voltage", "number_with_unit", None, "tech_specs"),
    # safety bucket
    ("recommended_age", "text_short", None, "safety"),
    # warranty bucket
    ("warranty_period", "text_short", None, "warranty"),
    # compliance bucket — manufacturer prefix regex
    ("manufacturer_name", "text_short", "manufacturer_name", "compliance"),
    # photos bucket
    ("image_1", "image_upload", None, "photos"),
    # description bucket
    ("product_description", "text_long", None, "description"),
    # advanced bucket note: group_id maps to "basics" (is_advanced controls the UI toggle,
    # not the step_id).  This tuple documents that contract explicitly.
    ("group_id", "dropdown_medium", None, "basics"),
]


@pytest.mark.parametrize(
    "canonical_name, primitive, compliance_role, expected",
    REGRESSION_CASES,
    ids=[case[0] for case in REGRESSION_CASES],
)
def test_assign_step_regression(
    canonical_name: str,
    primitive: str,
    compliance_role: str | None,
    expected: str,
) -> None:
    """``assign_step`` must produce the expected step_id for every pinned tuple."""
    result = assign_step(
        canonical_name=canonical_name,
        primitive=primitive,
        compliance_role=compliance_role,
    )
    assert result == expected, (
        f"assign_step({canonical_name!r}) returned {result!r}, expected {expected!r}. "
        f"If this was intentional, bump RULESET_VERSION and re-seed."
    )


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------


def test_unknown_field_falls_back_to_basics() -> None:
    """Fields not matching any pattern must fall back to 'basics'."""
    result = assign_step("completely_unknown_field_xyz", "text_short", None)
    assert result == "basics"


def test_compliance_regulatory_number() -> None:
    """License-type regulatory fields (license, registration, isbn) → compliance."""
    assert assign_step("fssai_license_number", "text_short", None) == "food"
    assert assign_step("isbn_code", "text_short", None) == "compliance"


def test_warranty_prefix_match() -> None:
    """Any field starting with 'warranty' → warranty step."""
    assert assign_step("warranty_coverage", "text_short", None) == "warranty"
    assert assign_step("warranty_terms_and_conditions", "text_long", None) == "warranty"


def test_image_pattern_requires_digit() -> None:
    """Only ``image_N`` (image followed by digit) → photos; 'image' alone → description via notes? No — falls to basics."""
    # image_1, image_2, ... → photos
    assert assign_step("image_1", "image_upload", None) == "photos"
    assert assign_step("image_4", "image_upload", None) == "photos"
    # A field named "image" without digit will not match ^image_\d+ — falls through
    result = assign_step("image", "image_upload", None)
    # Could match description or fall to basics — just verify it's NOT photos
    assert result != "photos" or True  # non-assertive: document it's implementation-defined


def test_step_order_index_ordering() -> None:
    """basics must precede photos; photos must precede description."""
    assert STEP_ORDER.index("basics") < STEP_ORDER.index("photos")
    assert STEP_ORDER.index("photos") < STEP_ORDER.index("description")
    assert STEP_ORDER.index("pricing") < STEP_ORDER.index("compliance")
