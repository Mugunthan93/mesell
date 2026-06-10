"""``dashboard`` — Seller tracking view (Feature 8) module.

Owner specialists: ``meesell-api-routes-builder`` (route + Pydantic schemas)
+ ``meesell-services-builder`` (read-aggregation composition) per
BACKEND_ARCHITECTURE.md §13 (LOCKED 2026-06-05; AMENDED 2026-06-07 — see §13.A.1).

**The purest demonstration of the modular monolith discipline.** Owns ZERO
tables. Has NO ``repository.py`` file in its subtree (deliberate structural
deviation from the §3.C canonical 7-file layout, locked at §13.D). Reads
NOTHING directly — every data access flows through:

* ``catalog.service.list_products(user_id, Pagination, db)``
  (§10.C + §16.B row 6)
* ``customer.service.get_onboarding_completeness(user_id, db)``
  (§8.C + §16.B row 7)

Both consumed services own ``scope_to_user(user_id)`` enforcement at their
respective repository layers per §10.D + §8.D. Dashboard never sees a raw
query; tenancy is upstream.

Per BACKEND_ARCHITECTURE.md §13 the module surfaces **1 endpoint**:

1. ``GET /api/v1/products`` — Paginated product listing (Feature 8)

The public router is exposed via ``dashboard_router`` so ``app/main.py``
can mount it with ``app.include_router(dashboard_router)``.

**§13.A.1 amendment scope (2026-06-07):** ``status_filter`` and ``search``
query parameters and the ``"exported"`` status Literal are deferred to V1.5
(bound to a §10 catalog amendment that extends ``Pagination`` + ``list_products``
+ ``list_paginated`` with the two predicates). V1 dashboard ships with
``page`` + ``limit`` only.
"""

from app.modules.dashboard.router import router as dashboard_router

__all__: list[str] = ["dashboard_router"]
