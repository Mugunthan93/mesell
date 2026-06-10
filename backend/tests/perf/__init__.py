"""§19.E performance budgets — 4 budgets locked in ``BACKEND_ARCHITECTURE.md``.

Files in this package:

* ``conftest.py``                       — perf-marker fixtures + budget helpers
* ``test_category_schema_p95.py``       — P95 schema fetch ≤ 50 ms cache hit / ≤ 200 ms miss
* ``test_category_browse_p95.py``       — P95 manual-browse ≤ 200 ms
* ``test_export_pipeline.py``           — End-to-end export ≤ 30 s
* ``test_ai_cost_average.py``           — Per-call AI cost ≤ ₹0.05 average (7-day window)

Every test in this package is marked ``@pytest.mark.slow`` AND
``@pytest.mark.perf`` per §19.E. Gated by ``PYTEST_RUN_SLOW=1`` env var; the
default per-PR run skips them. CI runs perf nightly.
"""
