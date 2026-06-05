"""Step assignment rules — canonical code lock for ``templates.schema_jsonb.fields[*].step_id``.

Source: §5.6.3 of ``docs/MVP_ARCHITECTURE.md`` (prose description).
This file IS the source of truth for step ID assignment.  The doc references
this module.  Do NOT edit the constants here without:
  1. Bumping ``RULESET_VERSION``.
  2. Re-running ``scripts/seed_all.py`` against dev and verifying that
     ``templates.schema_jsonb`` step_id values are unchanged (or intentionally
     updated and reviewed with the founder).
  3. Confirming ``backend/tests/test_step_assignment.py`` all pass.

Any quarterly Meesho refresh that modifies wizard steps must go through this
file — not through ad-hoc edits to ``scripts/build_template_schemas.py``.

Usage::

    from app.i18n.step_assignment import assign_step, STEP_ORDER, RULESET_VERSION
"""

from __future__ import annotations

import re

# Bump this whenever the ruleset changes.  Aligns with ``parser_version`` in
# the templates table so the seed pipeline can detect stale templates.
RULESET_VERSION = "v1"

# ---------------------------------------------------------------------------
# STEP_ASSIGNMENT — 14 ordered regex patterns.  First match wins.
# Matched against the *canonical* field name (snake_case).
# ---------------------------------------------------------------------------
STEP_ASSIGNMENT: list[tuple[re.Pattern[str], str]] = [
    # Images
    (re.compile(r"^image_\d+"), "photos"),
    # Compliance roles (manufacturer / packer / importer prefix)
    (re.compile(r"^(manufacturer|packer|importer)_"), "compliance"),
    # Description step
    (re.compile(r"(description|notes|ingredients)"), "description"),
    # Pricing
    (re.compile(r"(price|mrp|returns_price|defective_returns)"), "pricing"),
    # Inventory / weight / packaging dimensions
    (re.compile(
        r"^(inventory|net_weight|net_quantity|packaging_weight|"
        r"packaging_breadth|packaging_height|packaging_length)"
    ), "inventory"),
    # Sizing — apparel / footwear
    (re.compile(
        r"(size|bust|waist|hip|chest|length_size|width_size|height_size|"
        r"shoe_size|collar_size|inseam|thigh|sleeve|shoulder)"
    ), "sizing"),
    # Materials — apparel / home
    (re.compile(
        r"(fabric|material|pattern|weave|dye|finish|texture|"
        r"surface_treatment|plating|coating)"
    ), "materials"),
    # Food / grocery
    (re.compile(
        r"(veg_nonveg|shelf_life|preservatives|organic|fssai|food_type|"
        r"cuisine|flavor|flavour|sugar_free|added_sugar|energy|protein|fat|"
        r"carbohydrate|sodium|dietary|allergen|certifications)"
    ), "food"),
    # Tech specs — electronics
    (re.compile(
        r"(voltage|wattage|frequency|battery|watt|power|current|resistance|"
        r"capacitance|ram|rom|storage|processor|gpu|display_size|resolution|"
        r"operating_system|connectivity|bluetooth|wifi|hdmi|usb|port|"
        r"compatible_models|compatible_devices|camera|speaker|headphone|"
        r"audio|video|sensor|sim|antenna|touchscreen|refresh_rate|"
        r"clock_speed|core|bit_depth|sample_rate|latency)"
    ), "tech_specs"),
    # Safety — kids / appliances
    (re.compile(
        r"(recommended_age|age_group|safety|hazard|choking|flammable|"
        r"toxic|bis_isi|certification)"
    ), "safety"),
    # Warranty
    (re.compile(r"^warranty"), "warranty"),
    # Compliance-related regulatory numbers
    (re.compile(
        r"(license|registration|isbn|r_number|is_number|cm_l_number|bis|isi)"
    ), "compliance"),
    # Basics — universal catch-all fields
    (re.compile(
        r"^(product_name|variation|country_of_origin|generic_name|brand|"
        r"brand_name|product_id|sku_id|group_id|color|colour)"
    ), "basics"),
]

# ---------------------------------------------------------------------------
# STEP_ORDER — canonical wizard step ordering (lower index = earlier in wizard).
# The ``advanced`` bucket holds fields marked ``is_advanced=True`` (e.g. group_id)
# and always renders last — the frontend filters on is_advanced separately and
# renders the Advanced toggle regardless of step_id.
# ---------------------------------------------------------------------------
STEP_ORDER: list[str] = [
    "basics",
    "pricing",
    "inventory",
    "sizing",
    "materials",
    "food",
    "tech_specs",
    "safety",
    "warranty",
    "compliance",
    "photos",
    "description",
    "advanced",
]


def assign_step(
    canonical_name: str,
    primitive: str,  # noqa: ARG001 — reserved for future primitive-aware overrides
    compliance_role: str | None,  # noqa: ARG001 — reserved; compliance step already covered by regex
) -> str:
    """Return the wizard ``step_id`` for a field.

    The function encapsulates the dispatch logic previously inline in
    ``scripts/build_template_schemas.py:assign_step_id()``.

    Args:
        canonical_name: snake_case canonical field name (e.g. ``"product_name"``).
        primitive: The field's inferred primitive type (e.g. ``"text_short"``).
            Currently unused — the regex patterns in ``STEP_ASSIGNMENT`` are
            sufficient.  Accepted as a parameter so the signature is stable for
            future primitive-aware overrides without changing callers.
        compliance_role: The canonical compliance role if the field is a
            compliance field (e.g. ``"manufacturer_name"``), or ``None``.
            Currently unused for the same reason as ``primitive``.

    Returns:
        One of the step IDs listed in ``STEP_ORDER``, or ``"basics"`` if no
        pattern matches (fallback).

    Note on ``is_advanced``:
        The ``advanced`` bucket in ``STEP_ORDER`` is a display-layer concern
        managed by the ``is_advanced`` flag on each field, not by this
        function.  Fields with ``is_advanced=True`` (e.g. ``group_id``) receive
        a normal ``step_id`` from this function (``"basics"`` in the case of
        ``group_id``) and the frontend hides them behind the Advanced toggle
        independently of their step assignment.  See §12.4 for the design
        rationale.
    """
    for pattern, step_id in STEP_ASSIGNMENT:
        if pattern.search(canonical_name):
            return step_id
    return "basics"
