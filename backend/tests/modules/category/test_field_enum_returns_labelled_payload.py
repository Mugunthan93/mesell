"""Unit test §9.J #3 — field-enum lookup returns labelled payload + single-flight.

Per BACKEND_ARCHITECTURE.md §9.J unit 3:

    "Field-enum lookup returns labelled payload — every ``EnumEntry``
    carries ``{canonical, meesho, labels: {en: ...}}`` per ``MVP_ARCH
    §5.6.4``; ``single_flight=True`` protection enforced (two concurrent
    cache-miss requests fire ONE repository query, verified via call-
    count mock)."

The test uses a real ``(category_id, field_name)`` row from the seeded
``field_enum_values`` table (PK is composite (category_id, field_name)),
so the dev tunnel must be live.
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import text

from app.modules.category import service as category_service
from app.modules.category import repository as category_repo


async def _pick_first_fev(db):
    """Pick the first row in ``field_enum_values`` for the test."""
    result = await db.execute(
        text(
            "SELECT category_id, field_name FROM field_enum_values "
            "ORDER BY category_id, field_name LIMIT 1"
        )
    )
    row = result.first()
    assert row is not None, "field_enum_values is empty — seed required"
    return row[0], row[1]


async def test_field_enum_entries_carry_canonical_meesho_labels(db, use_live_valkey):
    """Every entry in enum_entries has {canonical, meesho, labels.en}."""
    category_id, field_name = await _pick_first_fev(db)

    payload = await category_service.get_field_enum(category_id, field_name, db)

    assert "enum_entries" in payload
    assert "total" in payload
    assert "truncated" in payload
    entries = payload["enum_entries"]
    assert isinstance(entries, list)
    assert len(entries) > 0

    for entry in entries:
        assert isinstance(entry, dict), entry
        assert set(entry.keys()) >= {"canonical", "meesho", "labels"}, (
            f"entry missing the 3 required keys: {entry}"
        )
        assert isinstance(entry["labels"], dict)
        assert "en" in entry["labels"], f"entry missing labels.en: {entry}"


async def test_field_enum_single_flight_dedupes_concurrent_misses(
    db, use_live_valkey, monkeypatch
):
    """Two concurrent cache-miss requests should fire the repo query ONCE."""
    category_id, field_name = await _pick_first_fev(db)

    call_count = {"n": 0}
    real_fetch = category_repo.fetch_field_enum_uncached

    async def counting_fetch(*args, **kwargs):
        call_count["n"] += 1
        # Sleep a touch so both callers actually start before the first
        # completes — this is the race the single_flight is meant to catch.
        await asyncio.sleep(0.05)
        return await real_fetch(*args, **kwargs)

    # Patch at the service-module attribute (service captured the name
    # via ``from app.modules.category import ... repository as category_repo``
    # so we patch the alias).
    monkeypatch.setattr(
        category_service.category_repo,
        "fetch_field_enum_uncached",
        counting_fetch,
    )

    # Pre-flush cache key.  use_live_valkey already flushes scratch DBs.
    # Fire two concurrent calls.
    results = await asyncio.gather(
        category_service.get_field_enum(category_id, field_name, db),
        category_service.get_field_enum(category_id, field_name, db),
    )

    # Both results are identical envelopes.
    assert results[0]["total"] == results[1]["total"]
    # Single-flight contract: the repository was hit at most ONCE for the
    # 2 concurrent cache-miss requests.
    assert call_count["n"] == 1, (
        f"single_flight failed: repo called {call_count['n']} times "
        f"(expected 1)"
    )


pytestmark = pytest.mark.usefixtures("db")
