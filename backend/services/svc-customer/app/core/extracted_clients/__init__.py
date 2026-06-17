"""HTTP-shim clients for the OUTBOUND callee customer consumes (FROZEN-0E).

Per spec §3.A + §16.G: the monolith ``customer.service`` did a cross-schema ORM
read against the ``categories`` table —

    from app.shared.models.category import Category as CategoryORM
    ...
    select(CategoryORM.super_id).distinct()   # customer/service.py:347

In svc-customer that becomes an HTTP shim (``category_client``) calling the
FROZEN-0E contract ``GET /internal/super-categories → list[str]``.  The
``CategoryORM`` import is DROPPED and ``_load_super_id_set``'s body is the ONLY
service.py logic edit (the second sanctioned edit being the dropped import).

R4 hybrid posture (§3.A / §0.8)
-------------------------------
During MS-3 the callee (category) is STILL IN-PROCESS in the monolith.  The
shim forwards to the MONOLITH ClusterIP
(``settings.MONOLITH_INTERNAL_BASE_URL``, default ``http://monolith-svc:8001``).
SUB_PLAN_0F (MS-4) re-points the base URL to category-svc via infra config —
NO code change here, and category-svc MUST implement the ``list[str]`` shape.

1 method / 1 callee:
* category_client.get_super_category_set
"""

from app.core.extracted_clients import category_client

__all__ = ["category_client"]
