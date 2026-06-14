"""HTTP-shim clients for the 2 cross-module callees catalog consumes.

Per SUB_PLAN_0H §H5 + §16.G: the monolith ``catalog.service`` imported 2 sibling
modules in-process (service.py:98-99) —

    from app.modules.category import service as category_service
    from app.modules.customer import service as customer_service

In svc-catalog those become HTTP shims that re-export the SAME
``<callee>_service`` symbol names, so the preserved call sites in ``service.py``
(the 8 outbound sites: category ×6 fetch_schema + ×1 exists + ×1 field-enum;
customer ×2) are UNCHANGED byte-for-byte:

    from app.core.extracted_clients import category_client as category_service
    from app.core.extracted_clients import customer_client as customer_service

REAL sibling pods (SUB_PLAN_0H §H5 — the FIRST extraction with live callees)
----------------------------------------------------------------------------
Unlike the MS-1..4 hybrid-posture extractions (whose callees were still
in-process in the monolith), catalog runs at MS-5 — so BOTH callees are already
EXTRACTED pods.  The shims forward to the REAL sibling ClusterIPs:
``settings.CATEGORY_SVC_BASE_URL`` (category-svc) + ``settings.CUSTOMER_SVC_BASE_URL``
(customer-svc), at the frozen ``/internal/*`` contract paths.

Methods / callees:
* category_client.assert_category_exists / fetch_schema / get_field_enum
  (→ category-svc; Open-Q #1 RESOLVED — assert_category_exists probes the
  already-served ``/schema`` endpoint as the existence gate, zero category-svc
  amendment; see category_client)
* customer_client.assert_eligible_for_super_id / get_compliance_block
  (→ customer-svc; both paths verified served by svc-customer internal_routes)

NO image_client (SUB_PLAN_0H §H5 R8): the ``service.py:828/:980``
``getattr(_image_module, "service")`` branch is DEAD V1 code (``get_image_refs``
does not exist on image-svc) — it travels verbatim, never fires, and catalog
authors NO image shim.
"""

from app.core.extracted_clients import (
    category_client,
    customer_client,
)

__all__ = [
    "category_client",
    "customer_client",
]
