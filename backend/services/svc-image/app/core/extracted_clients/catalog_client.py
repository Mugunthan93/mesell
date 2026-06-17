"""catalog-svc HTTP shim — re-exports the ``catalog_service`` symbol surface.

Shims the 1 cross-module method image consumes (spec §0.1 / §1 B1):

* :func:`assert_product_ownership` ← image/service.py:162 + :248
  → ``GET /internal/products/{id}/ownership-check`` (raises
  :class:`ProductNotFoundError` on 404).

This is the SAME shim pattern svc-export uses for ITS catalog callee — image
re-exports the SAME ``catalog_service`` symbol name so the 2 ``service.py``
call sites (``assert_product_ownership`` at :162 + :248) are byte-for-byte
UNCHANGED.

The method accepts the monolith call-site signature
``(product_id, user_id, db=db)`` — the ``db`` kwarg is accepted and IGNORED
(the shim talks HTTP, not SQL).

R4 hybrid posture (spec §0.1)
-----------------------------
catalog extracts LAST (MS-5).  Until then the callee is STILL IN-PROCESS in
the monolith, so the shim forwards to the MONOLITH ClusterIP
(``settings.MONOLITH_INTERNAL_BASE_URL``) at the frozen ``/internal/*``
contract path.  When catalog extracts, the only change is the base URL — the
shim transport + re-exported symbol name are unchanged.

Preserves the raise-on-not-owned semantics: 404 → :class:`ProductNotFoundError`
(the same 404-conflation leak-protection as the monolith
``catalog.exceptions.ProductNotFoundError`` — non-existent + cross-tenant +
soft-deleted all collapse to a single 404).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import MeesellError
from app.core.extracted_clients._transport import request_json


# ── Typed error raised on the monolith's 404 contract response ──────────────
class ProductNotFoundError(MeesellError):
    """Mirror of ``catalog.exceptions.ProductNotFoundError`` — 404 conflation
    of non-existent + cross-tenant per §4.C.
    """

    code = "catalog.product_not_found"
    status_code = 404
    validation_message_id = "catalog.product.not_found"

    def __init__(self, detail: str = "Product not found.") -> None:
        super().__init__(detail=detail)


# ── Shimmed method (re-exports the catalog_service symbol surface) ──────────
async def assert_product_ownership(
    product_id: UUID,
    user_id: UUID,
    db: Any = None,  # accepted + ignored — HTTP shim (call-site parity)
) -> None:
    """Ownership gate ← ``GET /internal/products/{id}/ownership-check``.

    Returns ``None`` on success; raises :class:`ProductNotFoundError` when the
    monolith responds 404 (not owned / does not exist).
    """
    import httpx

    try:
        await request_json(
            "GET",
            f"/internal/products/{product_id}/ownership-check",
            params={"user_id": str(user_id)},
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise ProductNotFoundError() from exc
        raise


__all__ = [
    "ProductNotFoundError",
    "assert_product_ownership",
]
