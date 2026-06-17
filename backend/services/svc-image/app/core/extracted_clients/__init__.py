"""HTTP-shim clients for the cross-module callee image consumes.

Per spec §0.1 + §16.G: the monolith ``image.service`` imported 1 sibling
module in-process —

    from app.modules.catalog import service as catalog_service

In svc-image this becomes an HTTP shim that re-exports the SAME
``catalog_service`` symbol name, so the 2 call sites in ``service.py``
(``assert_product_ownership`` at :162 + :248) are UNCHANGED byte-for-byte:

    from app.core.extracted_clients import catalog_client as catalog_service

R4 hybrid posture (spec §0.1)
-----------------------------
catalog extracts LAST (MS-5).  Until then the callee is STILL IN-PROCESS in
the monolith.  The shim forwards to the MONOLITH ClusterIP
(``settings.MONOLITH_INTERNAL_BASE_URL``, default ``http://monolith-svc:8001``)
at the frozen ``/internal/*`` contract path.  When catalog extracts, the only
change is the base URL — the shim transport and re-exported symbol name are
unchanged.

1 method / 1 callee:
* catalog_client.assert_product_ownership
"""

from app.core.extracted_clients import catalog_client

__all__ = [
    "catalog_client",
]
