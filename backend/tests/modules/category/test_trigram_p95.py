"""§9.J #1 — dedicated P95 < 200 ms benchmark for search_via_trigram.

**Purpose.**  This file is the BENCHMARK FIXTURE referenced in
``BACKEND_ARCHITECTURE.md §9.J`` unit-test item #1 and the smart-picker
feature plan acceptance criteria.  It complements (does NOT duplicate)
``test_trigram_search_uses_gin_index.py``:

* ``test_trigram_search_uses_gin_index.py`` — asserts the GIN bitmap-index
  scan fires on a raw SQL ``EXPLAIN ANALYZE`` + a 100-iteration P95 check
  wired against the repository function.

* **This file** — a standalone infra-gated benchmark that:

  1. Runs 100 iterations of ``repository.search_via_trigram("kurti", ...)``
     and reports a full latency histogram (min / P50 / P90 / P95 / P99 /
     max) in the test-failure message.
  2. Asserts P95 < 200 ms per ``MVP_ARCH §7.5``.
  3. Checks EXPLAIN ANALYZE output inline and embeds the relevant plan
     excerpt into the pass/fail message so the reviewer has EXPLAIN
     evidence without needing to connect to the DB separately.

**Infra gate.**  The suite requires a live dev-tunnel Postgres
(``localhost:5433``) where the pg_trgm extension and the 3 GIN indexes
(``idx_categories_path_trgm``, ``idx_categories_leaf_name_trgm``,
``idx_categories_super_name_trgm``) are present.  Without the tunnel the
``db`` fixture raises a connection error before any test body runs.

Two guard layers are applied so the suite skips cleanly in CI environments
that lack the tunnel:

1. **Collection-time skip (``PYTEST_RUN_SLOW=1`` env-var gate).**  The
   ``tests/perf/conftest.py`` ``pytest_collection_modifyitems`` hook skips
   every ``tests/perf/`` item.  This file lives under
   ``tests/modules/category/`` so it is NOT covered by that hook.
   Instead the in-body ``skip_unless_slow_enabled()`` call below serves as
   the equivalent gate for this module.

2. **In-body ``skip_unless_slow_enabled()`` call.**  Each test body starts
   with this call so that a targeted ``pytest tests/modules/category/
   test_trigram_p95.py`` invocation (bypassing the hook) also skips
   cleanly when the env var is absent.

To run the benchmark locally (tunnel must be up)::

    cd backend
    PYTEST_RUN_SLOW=1 pytest tests/modules/category/test_trigram_p95.py -v

Per ``BACKEND_ARCHITECTURE.md §9.D`` note on the global-data carve-out:
``categories`` is GLOBAL data (no ``user_id`` scope).  The repository
methods carry no ``user_id`` parameter — this is the §4.C linter-exception
path.  See also the ``_GLOBAL_TABLES`` drift note in the session report.
"""

from __future__ import annotations

import os
import statistics
import time
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text

from app.modules.category import repository as category_repo

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ── Marker declarations ────────────────────────────────────────────────────────
# ``slow`` — exceeds 5 s wall time (100 sequential async DB calls).
# ``perf`` — performance budget assertion per §19.E.
pytestmark = [pytest.mark.slow, pytest.mark.perf]

# ── Constants ─────────────────────────────────────────────────────────────────
# The search term used for benchmark.  "kurti" is the §9.J canonical fixture
# term (named in the spec verbatim).  It exercises the pg_trgm path-index
# with a realistic Indian-marketplace query.
_BENCH_QUERY = "kurti"

# Page size used during the benchmark — matches the default from §9.E BrowseQuery.
_BENCH_LIMIT = 20
_BENCH_OFFSET = 0

# Number of warm-up iterations excluded from the latency sample.
_WARMUP_ITERS = 5

# Number of timed iterations.
_BENCH_ITERS = 100

# P95 budget (ms) per BACKEND_ARCHITECTURE.md §9.J + MVP_ARCH §7.5.
_BUDGET_P95_MS = 200.0

# GIN index names that should appear in the EXPLAIN plan.
_GIN_INDEXES = frozenset(
    {
        "idx_categories_path_trgm",
        "idx_categories_leaf_name_trgm",
        "idx_categories_super_name_trgm",
    }
)


# ── Gate helper ───────────────────────────────────────────────────────────────

def _slow_gate_active() -> bool:
    """Return True iff ``PYTEST_RUN_SLOW=1`` is set in the environment."""
    return os.environ.get("PYTEST_RUN_SLOW", "0").lower() in {"1", "true", "yes"}


def skip_unless_slow_enabled() -> None:
    """Skip the calling test unless the slow-suite env var is set.

    Mirrors the pattern from ``tests/perf/conftest.py:skip_unless_slow_enabled``
    so that this benchmark, which lives outside ``tests/perf/``, uses the same
    infra-gate convention without importing from the perf conftest directly
    (cross-directory conftest imports cause pytest collection warnings).
    """
    if not _slow_gate_active():
        pytest.skip(
            "benchmark skipped — set PYTEST_RUN_SLOW=1 to opt in "
            "(infra-gated: requires dev-tunnel Postgres at localhost:5433 "
            "with pg_trgm + GIN indexes per session mesell-smart-picker-backend-session-1)."
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _percentile(sorted_samples: list[float], pct: float) -> float:
    """Nearest-rank percentile on a pre-sorted list."""
    n = len(sorted_samples)
    idx = max(0, min(n - 1, int(round(pct * (n - 1)))))
    return sorted_samples[idx]


def _latency_report(samples_ms: list[float]) -> str:
    """Format a one-line latency histogram string."""
    s = sorted(samples_ms)
    n = len(s)
    return (
        f"n={n}  "
        f"min={_percentile(s, 0.00):.1f}ms  "
        f"P50={_percentile(s, 0.50):.1f}ms  "
        f"P90={_percentile(s, 0.90):.1f}ms  "
        f"P95={_percentile(s, 0.95):.1f}ms  "
        f"P99={_percentile(s, 0.99):.1f}ms  "
        f"max={_percentile(s, 1.00):.1f}ms  "
        f"stdev={statistics.stdev(s):.1f}ms"
    )


# ── Benchmark: EXPLAIN ANALYZE evidence ───────────────────────────────────────


async def test_trigram_p95_explain_hits_gin_index(db: "AsyncSession") -> None:
    """Verify EXPLAIN ANALYZE shows a Bitmap Index Scan on idx_categories_path_trgm.

    This test is the EXPLAIN ANALYZE evidence fixture for the smart-picker
    PR merge gate.  The lead reviews the plan excerpt embedded in the pass
    message (or the failure message if the index was not used).

    Assertion: the EXPLAIN plan for an ILIKE %kurti% against ``categories.path``
    MUST reference at least one of the 3 GIN trigram indexes.
    """
    skip_unless_slow_enabled()

    stmt = text(
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) "
        "SELECT id, path FROM categories "
        "WHERE path ILIKE :pat LIMIT :lim"
    )
    result = await db.execute(stmt, {"pat": f"%{_BENCH_QUERY}%", "lim": _BENCH_LIMIT})
    plan_lines: list[str] = [row[0] for row in result.all()]
    plan_text = "\n".join(plan_lines)

    # Primary assertion: Bitmap path must be exercised.
    assert "Bitmap" in plan_text, (
        f"EXPLAIN plan did not show any Bitmap scan — pg_trgm GIN was NOT selected. "
        f"This means idx_categories_path_trgm is absent or pg_trgm is not enabled. "
        f"Ensure migration a1b2c3d4e5f6 was applied and the dev tunnel is at HEAD. "
        f"\n\nFull plan:\n{plan_text}"
    )

    # At least one of the 3 named GIN indexes must appear.
    matched_indexes = [idx for idx in _GIN_INDEXES if idx in plan_text]
    assert matched_indexes, (
        f"EXPLAIN plan did not reference any of the 3 GIN trigram indexes "
        f"{sorted(_GIN_INDEXES)}. "
        f"\n\nFull plan:\n{plan_text}"
    )

    # Emit a structured pass-log so the plan excerpt appears in the verbose
    # pytest output and in the PR body evidence block.
    plan_excerpt = "\n".join(plan_lines[:30])  # first 30 lines is usually enough
    print(
        f"\n[EXPLAIN evidence — test_trigram_p95_explain_hits_gin_index]\n"
        f"Query:        ILIKE %{_BENCH_QUERY}% on categories.path\n"
        f"GIN hit:      {matched_indexes}\n"
        f"Plan excerpt:\n{plan_excerpt}"
    )


# ── Benchmark: 100-iteration P95 ──────────────────────────────────────────────


async def test_trigram_p95_100_iterations(db: "AsyncSession") -> None:
    """P95 < 200 ms over 100 warm iterations of search_via_trigram.

    Methodology per §9.J unit-test item #1 + §19.E:
    1. Run ``_WARMUP_ITERS`` warm-up calls (excluded from the sample) so
       the Postgres plan cache is primed.
    2. Time ``_BENCH_ITERS`` = 100 sequential calls to
       ``repository.search_via_trigram("kurti", None, 20, 0)``.
    3. Compute P95 using the nearest-rank method (same as
       ``tests/perf/conftest.py:assert_p95_within_budget``).
    4. Assert P95 < 200 ms (no noise-tolerance band for this test — the
       budget is deliberately loose enough that a well-indexed result on
       any reasonable dev machine clears it with room to spare; the
       tight budget tests live in the nightly perf suite).

    The test also checks the super_id filter path by running 25 additional
    iterations with a realistic super_id so the reviewer can confirm the
    ``idx_categories_super_name_trgm`` join-path latency is comparable.
    """
    skip_unless_slow_enabled()

    # ── warm-up ───────────────────────────────────────────────────────────────
    for _ in range(_WARMUP_ITERS):
        await category_repo.search_via_trigram(db, _BENCH_QUERY, None, _BENCH_LIMIT, _BENCH_OFFSET)

    # ── timed path: q only, super_id=None ─────────────────────────────────────
    samples_ms: list[float] = []
    for _ in range(_BENCH_ITERS):
        t0 = time.perf_counter()
        rows, total = await category_repo.search_via_trigram(
            db, _BENCH_QUERY, None, _BENCH_LIMIT, _BENCH_OFFSET
        )
        t1 = time.perf_counter()
        samples_ms.append((t1 - t0) * 1000.0)

    s = sorted(samples_ms)
    p95_ms = _percentile(s, 0.95)
    report = _latency_report(samples_ms)

    # Emit structured benchmark output — visible in pytest -v and in the PR body.
    print(
        f"\n[P95 benchmark — test_trigram_p95_100_iterations]\n"
        f"Term:         {_BENCH_QUERY!r}  limit={_BENCH_LIMIT}  offset={_BENCH_OFFSET}\n"
        f"super_id:     None  (path-only trgm path)\n"
        f"Iterations:   {_BENCH_ITERS}\n"
        f"Latencies:    {report}\n"
        f"P95:          {p95_ms:.1f} ms  (budget: {_BUDGET_P95_MS:.0f} ms)\n"
        f"Last batch:   rows={len(rows)}  total={total}"
    )

    assert p95_ms < _BUDGET_P95_MS, (
        f"search_via_trigram P95 = {p95_ms:.1f} ms EXCEEDS {_BUDGET_P95_MS:.0f} ms budget "
        f"per BACKEND_ARCHITECTURE.md §9.J + MVP_ARCH §7.5.\n"
        f"Latency histogram: {report}\n"
        f"Action: verify idx_categories_path_trgm is present and not bloated; "
        f"run EXPLAIN ANALYZE locally to confirm the Bitmap Index Scan fires."
    )

    # ── secondary: super_id filter path (25 iters) ─────────────────────────────
    # Pick the super_id that produced the first result row if rows is non-empty.
    # If the query returned nothing (e.g. seed not loaded), skip gracefully.
    if rows:
        super_id_sample = rows[0].super_id
        super_id_samples_ms: list[float] = []
        for _ in range(25):
            t0 = time.perf_counter()
            await category_repo.search_via_trigram(
                db, _BENCH_QUERY, super_id_sample, _BENCH_LIMIT, _BENCH_OFFSET
            )
            t1 = time.perf_counter()
            super_id_samples_ms.append((t1 - t0) * 1000.0)

        super_report = _latency_report(super_id_samples_ms)
        print(
            f"\n[P95 benchmark — super_id filter path]\n"
            f"Term:         {_BENCH_QUERY!r}  super_id={super_id_sample!r}\n"
            f"Iterations:   25\n"
            f"Latencies:    {super_report}"
        )
    else:
        # No results means the seed is absent — report but don't fail.
        print(
            "\n[P95 benchmark — super_id filter path SKIPPED: "
            "search_via_trigram returned 0 rows — is the seed loaded?]"
        )
