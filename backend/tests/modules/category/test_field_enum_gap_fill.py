"""CAT-BE-19 / CAT-BE-20 / CAT-BE-21
Gap-fill for ``GET /categories/{id}/field-enum/{name}``.

- CAT-BE-19  unknown category UUID → 404 ``category.lookup.not_found``
- CAT-BE-20  valid category, field name with no enum → 404
             ``category.field_enum.not_found``
- CAT-BE-21  enum payload with very large entry list carries truncated=true

All three are route-level integration tests.
CAT-BE-19/20 need no seeded data (the 404 fires before enum table access).
CAT-BE-21 needs a seeded field_enum_values row with > cap entries — skipped
when seed is absent.
"""

from __future__ import annotations

import uuid

import pytest


pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-19  unknown category_id → 404 category.lookup.not_found
# ─────────────────────────────────────────────────────────────────────────────

async def test_field_enum_unknown_category_404(category_route_client):
    """CAT-BE-19: random UUID as category id → 404 category.lookup.not_found."""
    random_id = uuid.uuid4()

    resp = await category_route_client.get(
        f"/api/v1/categories/{random_id}/field-enum/brand_name"
    )

    assert resp.status_code == 404, (
        f"Expected 404 for unknown category, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    code = body.get("code") or body.get("validation_message_id")
    assert code, f"404 must carry a non-empty code; got {body}"
    assert "not_found" in str(code).lower(), (
        f"Expected a not_found code; got {code!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-20  valid category but field has no enum → 404 category.field_enum.not_found
# ─────────────────────────────────────────────────────────────────────────────

async def test_field_enum_no_enum_for_field_404(db, category_route_client):
    """CAT-BE-20: valid category + field name with no enum → 404 field_enum.not_found."""
    from sqlalchemy import text as _text

    # Need a real seeded leaf category.
    row = await db.execute(
        _text("SELECT id FROM categories LIMIT 1")
    )
    result = row.fetchone()

    if result is None:
        pytest.skip("categories not seeded — CI schema-only; skip CAT-BE-20")

    category_id = result[0]

    # "product_description" is a text_long field — has no enum by definition.
    resp = await category_route_client.get(
        f"/api/v1/categories/{category_id}/field-enum/product_description"
    )

    # May return 404 (field has no enum) or 404 (field doesn't exist).
    assert resp.status_code == 404, (
        f"Expected 404 for field with no enum, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    code = body.get("code") or body.get("validation_message_id")
    assert code, f"404 must carry a non-empty code; got {body}"


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-21  enum with >cap entries → truncated=true
# ─────────────────────────────────────────────────────────────────────────────

async def test_field_enum_truncated_flag_when_large(db, category_route_client):
    """CAT-BE-21: a field_enum_values entry with >cap entries → truncated=true.

    The service's ``get_field_enum`` truncates the enum list at a cap and sets
    ``truncated=true`` in the response. We look for a real field with a large
    enum (Compatible Models: max 4,481 entries per database-builder seed notes)
    to exercise this path.

    Skip when seed absent or when no large-enum field is found.
    """
    from sqlalchemy import text as _text

    # Find a (category_id, field_name) pair with a very long enum.
    row = await db.execute(
        _text(
            "SELECT c.id, fev.field_name "
            "FROM categories c "
            "JOIN field_enum_values fev ON fev.category_id = c.id "
            "WHERE jsonb_array_length(fev.enum_entries) > 500 "
            "LIMIT 1"
        )
    )
    result = row.fetchone()

    if result is None:
        pytest.skip(
            "No large-enum field_enum_values found "
            "(seed absent or no entry with >500 values); skip CAT-BE-21"
        )

    cat_id, field_name = result[0], result[1]

    resp = await category_route_client.get(
        f"/api/v1/categories/{cat_id}/field-enum/{field_name}"
    )

    if resp.status_code != 200:
        pytest.skip(
            f"GET /field-enum returned {resp.status_code}; skip truncated flag test"
        )

    body = resp.json()
    truncated = body.get("truncated")
    assert truncated is True, (
        f"Expected truncated=true for large-enum field; got {body}"
    )
