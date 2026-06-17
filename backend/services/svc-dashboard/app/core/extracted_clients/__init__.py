"""HTTP-shim clients for the 2 cross-module callees dashboard consumes.

Per spec §3.A + §16.G: the monolith ``dashboard.service`` imported 2 sibling
modules in-process —

    from app.modules.catalog import service as catalog_service
    from app.modules.customer import service as customer_service

In svc-dashboard those become HTTP shims that re-export the SAME
``<callee>_service`` symbol names, so the 2 call sites in ``service.py`` are
UNCHANGED byte-for-byte:

    from app.core.extracted_clients import catalog_client as catalog_service
    from app.core.extracted_clients import customer_client as customer_service

R4 hybrid posture (§3.A / §0.8)
-------------------------------
During MS-2 the 2 callees are STILL IN-PROCESS in the monolith (catalog
extracts LAST at MS-5; customer at MS-3).  The shims therefore forward to the
MONOLITH ClusterIP (``settings.MONOLITH_INTERNAL_BASE_URL``, default
``http://monolith-svc:8001``) at the frozen ``/internal/*`` contract paths.
When the callee sub-plans (E customer / H catalog) extract those services, the
only change is the base URL — the shim transport and the re-exported symbol
names are unchanged.

2 methods / 2 callees (the LIGHTEST shim surface of any extraction):
* catalog_client.list_products
* customer_client.get_onboarding_completeness
"""

from app.core.extracted_clients import (
    catalog_client,
    customer_client,
)

__all__ = [
    "catalog_client",
    "customer_client",
]
