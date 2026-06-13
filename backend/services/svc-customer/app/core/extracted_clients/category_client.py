"""category-svc HTTP shim — the OUTBOUND super-categories read (FROZEN-0E).

customer is the CALLER here.  This shim REPLACES the cross-schema ORM read at
the monolith ``customer/service.py:347``
(``SELECT DISTINCT super_id FROM categories`` via ``CategoryORM``) — see spec
§16.G + §2.D ("never SQL across a schema boundary").

FROZEN-0E contract (customer-owned — SUB_PLAN_0F MS-4 must conform):

* :func:`get_super_category_set` → ``GET /internal/super-categories`` →
  ``list[str]`` (distinct ``super_id`` values).

The frozen response shape is ``list[str]`` (NOT ``list[SuperCategoryInfo]`` —
category-svc's draft at MS-4 must conform to ``list[str]``).  The list is
returned as-is to the customer service's ``_load_super_id_set`` loader, which
caches it (``customer.super_category_set``, TTL 3600 s) and the cached accessor
``_get_super_id_set`` wraps it in a ``set`` for O(1) membership checks.

R4 hybrid posture (§3.A / §0.8)
-------------------------------
During MS-3 the callee (category) is STILL IN-PROCESS in the monolith.  The
shim forwards to the MONOLITH ClusterIP
(``settings.MONOLITH_INTERNAL_BASE_URL``, default ``http://monolith-svc:8001``)
at the frozen ``/internal/super-categories`` path.  When SUB_PLAN_0F (MS-4)
extracts category-svc, the ONLY change is the base URL (infra config) — the
shim transport and the re-exported symbol surface are unchanged.

The user JWT + X-Request-ID are forwarded by ``_transport`` from the per-request
context populated by ``RequestContextMiddleware`` (API path).
"""

from __future__ import annotations

from app.core.extracted_clients._transport import request_json


async def get_super_category_set() -> list[str]:
    """Distinct ``super_id`` set ← ``GET /internal/super-categories`` (FROZEN-0E).

    Returns the FROZEN ``list[str]`` of distinct super_ids.  The customer
    service's ``_load_super_id_set`` loader calls this in place of the original
    ``SELECT DISTINCT super_id FROM categories`` ORM read.

    The list is returned verbatim (deserialized from the monolith JSON array).
    A non-list / non-string-element payload is a contract violation — the
    ``[str(item) ...]`` coercion below normalises element type defensively so
    the downstream cache (JSON round-trip) + ``set()`` membership check stay
    deterministic.
    """
    payload = await request_json("GET", "/internal/super-categories")
    # FROZEN-0E: payload is a JSON array of distinct super_id strings.
    return [str(item) for item in payload]


__all__ = ["get_super_category_set"]
