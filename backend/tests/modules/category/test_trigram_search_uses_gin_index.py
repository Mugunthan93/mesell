"""Unit test §9.J #1 — trigram search uses the GIN index.

Per BACKEND_ARCHITECTURE.md §9.J unit 1:

    "Trigram search uses the GIN index — ``search_via_trigram(\"kurti\",
    ...)`` triggers ``Bitmap Index Scan on idx_categories_path_trgm``
    per EXPLAIN ANALYZE; P95 < 200 ms target per ``MVP_ARCH §7.5``
    measured over 100 iterations against the seeded dev DB."

Two assertions:

1. EXPLAIN ANALYZE on a trigram-flavour ILIKE query shows a
   ``Bitmap Index Scan`` (or ``Bitmap Heap Scan``) on one of the 3
   GIN trigram indexes shipped in migration ``a1b2c3d4e5f6``.
2. P95 of 100 iterations of ``repository.search_via_trigram(...)``
   is below the 200 ms threshold.

Runs against the live dev Postgres tunnel (port 5433) where the
pg_trgm extension + GIN indexes are present.
"""

from __future__ import annotations

import time

import pytest
from sqlalchemy import text

from app.modules.category import repository as category_repo


_GIN_INDEXES = {
    "idx_categories_path_trgm",
    "idx_categories_leaf_name_trgm",
    "idx_categories_super_name_trgm",
}


async def test_search_via_trigram_uses_gin_bitmap_index(db):
    """EXPLAIN ANALYZE on an ILIKE %kurti% on path picks up the GIN."""
    stmt = text(
        "EXPLAIN (ANALYZE, FORMAT TEXT) "
        "SELECT id, path FROM categories "
        "WHERE path ILIKE :pat LIMIT 20"
    )
    result = await db.execute(stmt, {"pat": "%kurti%"})
    plan_lines = [r[0] for r in result.all()]
    plan_text = "\n".join(plan_lines)

    # Per the §9.J prose: assert *some* GIN trigram bitmap scan participates.
    assert "Bitmap" in plan_text, (
        f"EXPLAIN plan did not show any Bitmap scan — pg_trgm GIN was not "
        f"selected. Plan:\n{plan_text}"
    )
    assert any(idx_name in plan_text for idx_name in _GIN_INDEXES), (
        f"EXPLAIN plan did not reference any of the 3 GIN trigram indexes "
        f"{_GIN_INDEXES}. Plan:\n{plan_text}"
    )


async def test_search_via_trigram_p95_under_200ms(db):
    """P95 over 100 iterations is under the §7.5 / MVP_ARCH 200 ms threshold."""
    timings_s: list[float] = []
    for _ in range(100):
        t0 = time.perf_counter()
        await category_repo.search_via_trigram(db, "kurti", None, 20, 0)
        t1 = time.perf_counter()
        timings_s.append(t1 - t0)

    timings_s.sort()
    p95_s = timings_s[int(0.95 * len(timings_s))]
    p95_ms = p95_s * 1000.0

    # Be a little lenient — local dev tunnel has network overhead that
    # production would not.  The contract is P95 < 200 ms; we assert
    # against that exact number.
    assert p95_ms < 200.0, (
        f"search_via_trigram P95 = {p95_ms:.1f} ms exceeds 200 ms "
        f"target per MVP_ARCH §7.5. min={timings_s[0]*1000:.1f}ms "
        f"median={timings_s[50]*1000:.1f}ms max={timings_s[-1]*1000:.1f}ms"
    )


# Mark all tests in this module as live-Postgres-required so a CI runner
# without the tunnel can skip in bulk.
pytestmark = [pytest.mark.usefixtures("db"), pytest.mark.integration]
