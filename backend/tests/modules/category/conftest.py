"""Category-module test fixtures.

The §9.J unit tests run against the **live dev Postgres tunnel** on
port 5433 (the ``db`` fixture in the top-level ``tests/conftest.py``)
because §9 reads seeded reference data: 3,772 categories, 3,566
templates, 49,259 field_enum_values rows.  Without the seed there is
nothing meaningful to assert.

The pg_trgm extension + the 3 GIN indexes (idx_categories_path_trgm,
idx_categories_leaf_name_trgm, idx_categories_super_name_trgm) only
exist on the dev tunnel DB (shipped by migration ``a1b2c3d4e5f6``), so
the EXPLAIN ANALYZE Bitmap-Index-Scan assertion in
``test_trigram_search_uses_gin_index.py`` REQUIRES this fixture.

Added: ``_disable_category_cache`` autouse fixture (QA Wave-A gap fills)
-----------------------------------------------------------------------
Route-level gap tests (test_suggest_gap_fill, test_browse_gap_fill, etc.)
make ASGI requests against the app which calls ``app.core.cache.get_or_set``
internally.  That function connects to the app's configured Valkey instance
(port 6381) which is NOT available in the local test environment.
The autouse fixture patches ``get_or_set`` to a passthrough factory-call
so all category-module route tests run without a live app Valkey.

Note: this mirrors the identical pattern in tests/modules/catalog/conftest.py
(§10-CATALOG-D1 test isolation).
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_category_cache(monkeypatch):
    """Bypass the app Valkey cache for all category-module tests.

    Patches ``app.core.cache.get_or_set`` to call the factory directly,
    plus every consumer module that captured ``get_or_set`` by name at
    import time.  This keeps category route tests hermetic without
    requiring a live app Valkey on port 6381.
    """
    import app.core.cache as cache_mod

    async def _passthrough(key, factory, *, ttl=60, single_flight=False):
        return await factory()

    monkeypatch.setattr(cache_mod, "get_or_set", _passthrough)

    for mod_path in (
        "app.modules.category.service",
        "app.modules.customer.service",
    ):
        try:
            mod = __import__(mod_path, fromlist=["get_or_set"])
        except Exception:  # noqa: BLE001
            continue
        if hasattr(mod, "get_or_set"):
            monkeypatch.setattr(mod, "get_or_set", _passthrough)
