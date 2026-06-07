"""Unit test §9.J #2 — schema fetch envelope conformance.

Per BACKEND_ARCHITECTURE.md §9.J unit 2:

    "Schema fetch envelope conformance — ``fetch_schema(category_id)``
    returns a dict conforming to §5A.B (7 top-level keys present); every
    entry in ``fields[]`` carries the documented §5A.C field shape;
    count invariants hold (``total_count == compulsory_count +
    optional_count``); ``compliance_shape ∈ {\"standard\", \"collapsed\"}``."

The seeded ``templates.schema_jsonb`` field shape carries the §2.3 raw
24-key shape (the seed pipeline derives the §5A.C 9-key wizard view in
a future seed step).  This test asserts the envelope-level §5A.B
contract — the 7 top-level keys — and the documented set of keys per
field as they exist today in the seed.  Re-locked when the seed-time
§5A.C derivation lands.
"""

from __future__ import annotations

import random
from uuid import UUID

import pytest
from sqlalchemy import text

from app.modules.category import service as category_service


_ENVELOPE_KEYS = {
    "fields",
    "compulsory_count",
    "optional_count",
    "total_count",
    "wizard_step_count",
    "main_sheet_label",
    "compliance_shape",
}

_COMPLIANCE_SHAPE_VALUES = {"standard", "collapsed"}

# Per the seeded shape (§2.3 raw 24-key form).  Tested at the keys that
# the FieldSpec contract in §5A.C derives ITS 9 keys from.
_SEED_FIELD_KEYS_REQUIRED = {
    "canonical_name",
    "data_type",
    "primitive",
    "marker",
    "is_advanced",
}


async def _pick_random_category_ids(db, n: int) -> list[UUID]:
    """Sample ``n`` distinct category_ids from the seeded ``categories`` table."""
    result = await db.execute(text("SELECT id FROM categories ORDER BY id"))
    ids = [row[0] for row in result.all()]
    random.seed(42)  # deterministic for test repeatability
    sample = random.sample(ids, min(n, len(ids)))
    return [UUID(str(i)) if not isinstance(i, UUID) else i for i in sample]


async def test_fetch_schema_envelope_has_all_seven_top_level_keys(db, use_live_valkey):
    """For each of 5 random category_ids the envelope carries all 7 §5A.B keys."""
    ids = await _pick_random_category_ids(db, 5)
    for cid in ids:
        envelope = await category_service.fetch_schema(cid, db)
        assert _ENVELOPE_KEYS.issubset(set(envelope.keys())), (
            f"envelope for category_id={cid} missing keys "
            f"{_ENVELOPE_KEYS - set(envelope.keys())}"
        )


async def test_fetch_schema_compliance_shape_in_locked_set(db, use_live_valkey):
    """compliance_shape ∈ {standard, collapsed} per §5A.B."""
    ids = await _pick_random_category_ids(db, 5)
    for cid in ids:
        envelope = await category_service.fetch_schema(cid, db)
        assert envelope["compliance_shape"] in _COMPLIANCE_SHAPE_VALUES


async def test_fetch_schema_count_invariant(db, use_live_valkey):
    """total_count == compulsory_count + optional_count per §5A.B."""
    ids = await _pick_random_category_ids(db, 5)
    for cid in ids:
        envelope = await category_service.fetch_schema(cid, db)
        assert (
            envelope["total_count"]
            == envelope["compulsory_count"] + envelope["optional_count"]
        ), (
            f"count invariant violated for {cid}: "
            f"{envelope['compulsory_count']} + {envelope['optional_count']} "
            f"!= {envelope['total_count']}"
        )


async def test_fetch_schema_fields_carry_documented_keys(db, use_live_valkey):
    """Each fields[] entry has the §5A.C-derived required key set.

    The seeded shape (§2.3 raw form) carries 24 keys per field; we
    assert the 5 keys the §5A.C 9-key wizard view DERIVES FROM are
    always present.  The §5A.C derivation itself lands at the seed-
    time §5A.C step; tests for the strict 9-key set live in
    ``tests/test_per_field_shape_keys.py`` (already-shipped fixture).
    """
    ids = await _pick_random_category_ids(db, 5)
    for cid in ids:
        envelope = await category_service.fetch_schema(cid, db)
        fields = envelope.get("fields") or []
        assert isinstance(fields, list)
        assert len(fields) > 0, f"no fields for category_id={cid}"
        for fld in fields:
            assert isinstance(fld, dict)
            missing = _SEED_FIELD_KEYS_REQUIRED - set(fld.keys())
            assert not missing, (
                f"field {fld.get('canonical_name', '?')} for "
                f"category_id={cid} missing keys {missing}"
            )


pytestmark = pytest.mark.usefixtures("db")
