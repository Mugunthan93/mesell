"""§19.E perf budget 2 — P95 category manual-browse latency.

Locked budget (BACKEND_ARCHITECTURE.md §19.E + ``MVP_ARCH §7.5`` + §9.B.2):

* P95 ≤ **200 ms** for the trigram-search ILIKE path against the
  ``idx_categories_path_trgm`` GIN index (shipped in session 2 G4
  migration ``a1b2c3d4e5f6``).

Methodology:

1. Pick a representative search term that exercises the GIN index
   (per coordinator memory G4 verification, ``"kurti"`` hits
   ``Bitmap Index Scan on idx_categories_path_trgm``).
2. Measure 30 calls to ``service.browse(query=...)`` and assert
   P95 within budget + 10% noise band.
"""

from __future__ import annotations

import time

import pytest

from tests.perf.conftest import (
    assert_p95_within_budget,
    skip_unless_slow_enabled,
)

pytestmark = [pytest.mark.slow, pytest.mark.perf]

# §19.E locked budget.
BUDGET_BROWSE_MS = 200.0

# Representative search terms — exercise different super-category branches.
SAMPLE_QUERIES: tuple[str, ...] = (
    "kurti",
    "saree",
    "phone",
    "shoes",
    "watch",
)


@pytest.mark.asyncio
async def test_p95_category_browse(db) -> None:
    """P95 trigram browse query ≤ 200 ms per §19.E + ``MVP_ARCH §7.5``.

    Per §9.D the browse query shape is::

        SELECT id, path, leaf_name, super_name, super_id,
               GREATEST(similarity(path, :q), ...) AS score
        FROM categories
        WHERE path ILIKE :pattern OR ...
        ORDER BY score DESC
        LIMIT 50;

    The GIN trigram index on ``categories.path`` is the load-bearing index.
    """
    skip_unless_slow_enabled()

    from app.modules.category import service as category_service

    samples: list[float] = []
    for i in range(30):
        query = SAMPLE_QUERIES[i % len(SAMPLE_QUERIES)]
        start = time.perf_counter()
        await category_service.browse(query=query, db=db)
        samples.append((time.perf_counter() - start) * 1000.0)

    assert_p95_within_budget(
        samples,
        budget_ms=BUDGET_BROWSE_MS,
        label="category.browse P95 (trigram GIN)",
    )
