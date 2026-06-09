"""``catalog`` — Product CRUD, autosave, Auto-fill, Live Preview module.

Owner specialists: ``meesell-api-routes-builder`` (routes + Pydantic
schemas) + ``meesell-services-builder`` (business logic, AI Auto-fill
orchestration, schema-driven validation, autosave drafts) per
BACKEND_ARCHITECTURE.md §10 (LOCKED 2026-06-05).

The central spine of the application (per §2.4): catalog has only 2
outbound service calls (``customer`` + ``category``) but is called BY
**four** downstream modules — ``image`` (assert_product_ownership),
``pricing`` (assert_product_ownership), ``dashboard`` (list_products +
get_validation_summary), and ``export`` (get_product_for_export) — making
it the most-called module in the architecture.

Per BACKEND_ARCHITECTURE.md §10 the module surfaces 6 endpoints:

1. ``POST   /api/v1/products``                       — create product
2. ``PATCH  /api/v1/products/{id}``                  — update fields + autosave
3. ``POST   /api/v1/products/{id}/autofill``         — AI Auto-fill
4. ``GET    /api/v1/products/{id}/preview``          — Live Product Preview
5. ``DELETE /api/v1/products/{id}``                  — soft delete
6. ``GET    /api/v1/products/{id}/draft``            — draft recovery

The public router is exposed via ``catalog_router`` so ``app/main.py``
can mount it with ``app.include_router(catalog_router)``.
"""

from app.modules.catalog.router import router as catalog_router

__all__: list[str] = ["catalog_router"]
