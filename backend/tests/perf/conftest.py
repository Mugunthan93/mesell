"""§19.E perf-suite fixtures + budget helpers.

Each perf test file imports :func:`assert_p95_within_budget` to express the
"P95 latency ≤ X ms" assertion uniformly. The 10% noise-tolerance band
from §19.E ("perf regression policy") is encoded in the helper — a 1-shot
measurement that exceeds budget * 1.10 fails the test.

Perf-suite invocation::

    PYTEST_RUN_SLOW=1 pytest tests/perf/

CI runs nightly; per-PR runs do NOT execute this suite (the
``@pytest.mark.slow`` + ``PYTEST_RUN_SLOW=1`` gate keeps it off the fast lane).

Suite-wide skip mechanism
-------------------------
The :func:`pytest_collection_modifyitems` hook below applies a
``pytest.mark.skip`` to every collected test in ``tests/perf/`` unless
``PYTEST_RUN_SLOW=1``. This is the BEFORE-fixture-instantiation gate —
without it the ``db`` fixture would attempt a live Postgres connection
during fast-lane runs and error out instead of skipping cleanly.
"""

from __future__ import annotations

import os
import statistics

import pytest


# ── §19.E noise-tolerance band — 10% above budget per the locked perf
#    regression policy. Beyond 10% indicates a real regression that blocks
#    merge per §19.E "Performance regression policy".
NOISE_TOLERANCE_PCT: float = 10.0


def _slow_gate_active() -> bool:
    """Return True iff the perf suite was explicitly opted in."""
    return os.environ.get("PYTEST_RUN_SLOW", "0").lower() in {"1", "true", "yes"}


def skip_unless_slow_enabled() -> None:
    """Skip the test unless the slow-suite env var is set.

    Defensive — the collection-time hook below already skips every test in
    ``tests/perf/`` when the gate is off. This in-body helper covers the
    case where a single perf test is invoked by node id (which bypasses
    collection-time filtering for sibling files).
    """
    if not _slow_gate_active():
        pytest.skip(
            "perf suite skipped — set PYTEST_RUN_SLOW=1 to opt in "
            "(§19.E nightly-only policy)."
        )


def pytest_collection_modifyitems(config, items):
    """Skip every test under ``tests/perf/`` unless ``PYTEST_RUN_SLOW=1``.

    This runs BEFORE fixture instantiation, so the ``db`` fixture never
    tries to open a live Postgres connection during fast-lane PR runs.
    Implements the §19.G "stage 6 (nightly only)" gate at the
    collection-time level — the cleanest way to keep the perf suite off
    the fast lane without sprinkling decorators on every test.
    """
    if _slow_gate_active():
        return
    skip_marker = pytest.mark.skip(
        reason="§19.E perf suite skipped — set PYTEST_RUN_SLOW=1 to opt in."
    )
    for item in items:
        # Match by file path so this hook only affects tests/perf/*.
        if "tests/perf/" in str(item.fspath).replace("\\", "/"):
            item.add_marker(skip_marker)


def assert_p95_within_budget(
    samples: list[float],
    *,
    budget_ms: float,
    label: str,
    tolerance_pct: float = NOISE_TOLERANCE_PCT,
) -> None:
    """Assert the P95 of ``samples`` (in milliseconds) is within budget.

    Args:
        samples: list of per-call latencies in milliseconds.
        budget_ms: locked budget per §19.E (e.g. 50 ms for schema cache hit).
        label: human-readable test identifier for failure messages.
        tolerance_pct: noise band — default 10% per §19.E.

    Raises:
        AssertionError when P95 exceeds ``budget_ms * (1 + tolerance_pct/100)``.
    """
    if not samples:
        pytest.fail(f"{label!r}: no samples — perf test produced empty data.")

    samples_sorted = sorted(samples)
    # statistics.quantiles uses Q9 inclusive method; this matches §19.E intent.
    # For 100 samples, quantiles(...,n=100)[94] is the 95th percentile.
    n = len(samples_sorted)
    if n < 10:
        # Belt-and-braces — perf tests should sample at least 20 calls.
        pytest.fail(
            f"{label!r}: too few samples ({n} < 10) — P95 measurement is "
            "statistically meaningless."
        )

    # Compute P95 using nearest-rank method (consistent across Python versions).
    p95_idx = max(0, int(round(0.95 * (n - 1))))
    p95 = samples_sorted[p95_idx]

    limit = budget_ms * (1.0 + tolerance_pct / 100.0)
    if p95 > limit:
        pytest.fail(
            f"{label!r}: P95={p95:.1f} ms exceeds budget {budget_ms:.1f} ms "
            f"(+{tolerance_pct:.0f}% tolerance → {limit:.1f} ms). "
            f"min={min(samples):.1f} median={statistics.median(samples):.1f} "
            f"max={max(samples):.1f} n={n}."
        )


def assert_value_within_budget(
    actual: float,
    *,
    budget: float,
    label: str,
    unit: str = "",
    tolerance_pct: float = NOISE_TOLERANCE_PCT,
) -> None:
    """Assert a single measured value is within the locked budget + tolerance.

    Used for the export-pipeline budget (≤ 30 s) and the AI-cost budget
    (≤ ₹0.05 average) where the §19.E budget is a scalar, not a P95.
    """
    limit = budget * (1.0 + tolerance_pct / 100.0)
    if actual > limit:
        pytest.fail(
            f"{label!r}: actual={actual:.4f}{unit} exceeds budget "
            f"{budget:.4f}{unit} (+{tolerance_pct:.0f}% → {limit:.4f}{unit})."
        )


# Re-export the gate so test files can write `skip_unless_slow_enabled()` at
# the top of every test body without an import boilerplate explosion.
__all__ = [
    "NOISE_TOLERANCE_PCT",
    "assert_p95_within_budget",
    "assert_value_within_budget",
    "skip_unless_slow_enabled",
]
