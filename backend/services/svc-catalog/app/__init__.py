"""svc-catalog — standalone catalog/product microservice (MS Sub-Plan H — THE SPINE).

Extracted from the monolith ``app.modules.catalog`` (BACKEND_ARCHITECTURE.md
§10 LOCKED 2026-06-05) per the validated MS extraction recipe.  THE LAST +
RISKIEST extraction: catalog is BOTH the heaviest CALLEE (4 inbound
``/internal/*`` shims: ownership-check / export-snapshot / list_products +
defensive validation-summary, consumed by image/pricing/export/dashboard) AND a
multi-callee CALLER (5 outbound HTTP shims: category ×3 + customer ×2).

The business logic (``service.py`` / ``repository.py`` / ``domain.py`` /
``exceptions.py``) is vendored byte-for-byte under the §16.G discipline; the
only changes vs the monolith are the 2 cross-module import-line rewires
(category/customer → HTTP shims) + the catalog module flattening
(``app.modules.catalog.X`` → ``app.X``).  ZERO call-site changes.

AI-CONSUMING (the 3rd + last AI service to extract): catalog runs the
``autofill.v1`` workload, so it VENDORS a trimmed ``ai_ops`` (the ``autofill_v1``
prompt ONLY — NOT smart_picker/watermark).  The ₹500 daily BUDGET BRAKE stays
SHARED/GLOBAL via the un-prefixed ``ai:*`` Valkey keyspace (H3.c).

Owns 3 TENANT-SCOPED tables — ``catalogs`` / ``products`` / ``product_drafts`` —
bound to the ``catalog`` Postgres schema (moved ``public`` → ``catalog`` in
MS-H Phase A).  ``scope_to_user`` on every product/catalog read (§10 leak rule).

NO Celery (catalog has no worker — autosave is synchronous).  The public router
mounts behind ``FEATURE_CATALOG_FORM_ENABLED`` (R9 / row-26 mount guard).

The package root re-exports nothing at import time — ``main.py`` mounts the
public + internal routers import-tolerantly so the app boots before
``router.py`` / ``internal_router.py`` (delivered by meesell-api-routes-builder,
Phase B) land.
"""
