"""HTTP-shim clients for the 2 cross-module callees pricing consumes.

Per spec §0.5 + §16.G: the monolith ``pricing.service`` imported 2 sibling
modules in-process (service.py:65-66) —

    from app.modules.catalog import service as catalog_service
    from app.modules.category import service as category_service

In svc-pricing those become HTTP shims that re-export the SAME
``<callee>_service`` symbol names, so the preserved call sites in ``service.py``
(:134, :165, :241) are UNCHANGED byte-for-byte:

    from app.core.extracted_clients import catalog_client as catalog_service
    from app.core.extracted_clients import category_client as category_service

R4 hybrid posture (spec §0.5 / §5)
----------------------------------
During MS-3 the 2 callees are STILL IN-PROCESS in the monolith (catalog
extracts LAST at MS-5/H; category at MS-F).  The shims therefore forward to the
MONOLITH ClusterIP (``settings.MONOLITH_INTERNAL_BASE_URL``, default
``http://monolith-svc:8001``) at the frozen ``/internal/*`` contract paths.
When the callee sub-plans (F category / H catalog) extract those services, the
only change is the base URL — the shim transport and the re-exported symbol
names are unchanged.

§0.6 contract items (NEW — the callee sub-plans must honor):
* catalog ``GET /internal/products/{id}/ownership-check`` is WIDENED to return
  ``{"category_id": "<uuid>"}`` on success (Sub-Plan H) — replaces the monolith
  shared-ORM ``db.get(ProductORM)`` read.
* category ``GET /internal/categories/{id}/commission`` is NEW vs MS-A
  (Sub-Plan F) — returns ``{"commission_pct": "<decimal-string>"}``, NEVER null.

Methods / callees:
* catalog_client.assert_product_ownership (+ get_category_id — §0.6)
* category_client.get_commission
"""

from app.core.extracted_clients import (
    catalog_client,
    category_client,
)

__all__ = [
    "catalog_client",
    "category_client",
]
