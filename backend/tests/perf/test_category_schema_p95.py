"""§19.E perf budget 1 — P95 category schema fetch.

Locked budgets (BACKEND_ARCHITECTURE.md §19.E + ``MVP_ARCH §6.6`` + §9.B.4):

* P95 ≤ **50 ms**  on cache HIT  (cached schema_jsonb in Valkey DB 3)
* P95 ≤ **200 ms** on cache MISS (cold fetch from PostgreSQL)

Methodology (per §19.E):

1. Pick a representative leaf-category ID from the live ``categories``
   table (the SeederLite seed populates ~14 super categories with leaves).
2. Warm the cache by calling ``service.fetch_schema(category_id)`` once.
3. Measure 50 cache-hit calls — assert P95 ≤ 50 ms (+10% noise tolerance).
4. Bump ``CACHE_VERSION`` to invalidate, then measure 20 cache-miss calls
   — assert P95 ≤ 200 ms (+10% tolerance).

This test is paired markers ``slow + perf``; CI runs nightly per §19.G stage 6.
"""

from __future__ import annotations

import time
import uuid

import pytest

from tests.perf.conftest import (
    assert_p95_within_budget,
    skip_unless_slow_enabled,
)

pytestmark = [pytest.mark.slow, pytest.mark.perf]


# §19.E locked budgets.
BUDGET_CACHE_HIT_MS = 50.0
BUDGET_CACHE_MISS_MS = 200.0


@pytest.mark.asyncio
async def test_p95_category_schema_cache_hit(db, valkey) -> None:
    """P95 schema fetch (cache hit) ≤ 50 ms per §19.E + ``MVP_ARCH §6.6``.

    Cache hit = Valkey DB 3 carries the ``schema:{cat_id}`` payload (§9.B
    + §15.C). The seed-time pre-warm hook (§4.D + ``MVP_ARCH §6.7``) loads
    the top-100 schemas at boot; this test re-warms in-loop to avoid
    coupling to the boot hook timing.
    """
    skip_unless_slow_enabled()

    # Lazy-import to keep collection cheap when the slow gate is off.
    from sqlalchemy import select

    from app.modules.category import service as category_service
    from app.shared.models.category import Category

    # Pick any leaf category from the seeded set.
    row = (
        await db.execute(
            select(Category.id).limit(1)  # leaf-only table (§9); is_leaf dropped (BE-CAT-ISLEAF-1)
        )
    ).first()
    if row is None:
        pytest.skip("no leaf category seeded — cannot measure schema fetch.")
    category_id: uuid.UUID = row[0]

    # Warm the cache so the timed loop sees hits only.
    await category_service.fetch_schema(category_id, db=db)

    samples: list[float] = []
    for _ in range(50):
        start = time.perf_counter()
        await category_service.fetch_schema(category_id, db=db)
        samples.append((time.perf_counter() - start) * 1000.0)

    assert_p95_within_budget(
        samples,
        budget_ms=BUDGET_CACHE_HIT_MS,
        label="category.fetch_schema P95 cache hit",
    )


@pytest.mark.asyncio
async def test_p95_category_schema_cache_miss(db, valkey) -> None:
    """P95 schema fetch (cache miss) ≤ 200 ms per §19.E + ``MVP_ARCH §6.6``.

    Forces a cold path by flushing the Valkey cache DB before each sample.
    """
    skip_unless_slow_enabled()

    from sqlalchemy import select

    from app.modules.category import service as category_service
    from app.shared.models.category import Category

    row = (
        await db.execute(
            select(Category.id).limit(1)  # leaf-only table (§9); is_leaf dropped (BE-CAT-ISLEAF-1)
        )
    ).first()
    if row is None:
        pytest.skip("no leaf category seeded — cannot measure schema fetch.")
    category_id: uuid.UUID = row[0]

    samples: list[float] = []
    for _ in range(20):
        # Cold path — flush the cache DB so the helper has to hit Postgres.
        try:
            await valkey["cache"].flushdb()
        except Exception:
            pass
        start = time.perf_counter()
        await category_service.fetch_schema(category_id, db=db)
        samples.append((time.perf_counter() - start) * 1000.0)

    assert_p95_within_budget(
        samples,
        budget_ms=BUDGET_CACHE_MISS_MS,
        label="category.fetch_schema P95 cache miss",
    )
