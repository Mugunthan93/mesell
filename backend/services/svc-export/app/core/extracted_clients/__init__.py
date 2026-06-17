"""HTTP-shim clients for the 4 cross-module callees export consumes.

Per spec §3.A + §16.G: the monolith ``export.service`` imported 4 sibling
modules in-process —

    from app.modules.catalog import service as catalog_service
    from app.modules.category import service as category_service
    from app.modules.customer import service as customer_service
    from app.modules.image import service as image_service

In svc-export those become HTTP shims that re-export the SAME
``<callee>_service`` symbol names, so the 7 call sites in ``service.py`` are
UNCHANGED byte-for-byte:

    from app.core.extracted_clients import catalog_client as catalog_service
    from app.core.extracted_clients import category_client as category_service
    from app.core.extracted_clients import customer_client as customer_service
    from app.core.extracted_clients import image_client as image_service

R4 hybrid posture (§3.A / §0.8)
-------------------------------
During Sub-Plan A the 4 callees are STILL IN-PROCESS in the monolith.  The
shims therefore forward to the MONOLITH ClusterIP
(``settings.MONOLITH_INTERNAL_BASE_URL``, default ``http://monolith-svc:8001``)
at the frozen ``/internal/*`` contract paths (spec §5).  When the callee
sub-plans (C image / E customer / F category / H catalog) extract those
services, the only change is the base URL — the shim transport and the
re-exported symbol names are unchanged.

6 methods / 4 callees:
* catalog_client.assert_product_ownership + get_product_for_export
* category_client.fetch_schema + get_field_enum
* customer_client.get_compliance_block
* image_client.list_images   (NOT get_image_bytes — §0.4 corrected the plan)
"""

from app.core.extracted_clients import (
    catalog_client,
    category_client,
    customer_client,
    image_client,
)

__all__ = [
    "catalog_client",
    "category_client",
    "customer_client",
    "image_client",
]
