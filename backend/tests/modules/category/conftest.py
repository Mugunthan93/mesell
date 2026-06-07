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

This file intentionally adds nothing — the upstream ``db`` fixture
(``tests/conftest.py:db``) is what we use.  Kept here as a marker for
future per-module fixtures (e.g. a pre-warmed Valkey cache fixture if
we need it).
"""

from __future__ import annotations
