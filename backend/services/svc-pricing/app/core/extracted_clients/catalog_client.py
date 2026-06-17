"""catalog-svc HTTP shim — re-exports the ``catalog_service`` symbol surface.

Shims the cross-module methods pricing consumes from catalog (spec §0.5 + §0.6):

* :func:`assert_product_ownership` ← catalog/service.py:919
  → ``GET /internal/products/{id}/ownership-check`` (raises
  :class:`ProductNotFoundError` on 404).  Used at the 2 byte-for-byte-preserved
  call sites service.py:134 + :241.
* :func:`get_category_id` ← the §0.6 resolution (NEW shim method, NOT a
  monolith symbol) → reads ``category_id`` from the WIDENED ownership-check
  response.  REPLACES the monolith's
  ``from app.shared.models.product import Product as ProductORM`` +
  ``db.get(ProductORM, product_id)`` (service.py:151-162) — which is an illegal
  cross-schema ORM read after extraction (§2.D HTTP-only).

§0.6 RESOLUTION — Option B (the catalog ownership shim is widened)
------------------------------------------------------------------
The monolith ``service.calculate`` read ``product.category_id`` via a SHARED-ORM
``db.get(ProductORM, product_id)`` to fetch the category needed for the
commission lookup.  After extraction that ORM read crosses the
``public.products`` schema boundary illegally.  Per spec §0.6 we picked
**Option B**: extend the catalog ``/internal/products/{id}/ownership-check``
``/internal/*`` endpoint to ALSO return ``category_id`` on the 200-success body.
Pricing reads ``category_id`` over HTTP via :func:`get_category_id` and the
``ProductORM`` import + ``db.get`` are DELETED.

CONTRACT ITEM for Sub-Plan H / catalog (NEW — must honor):
``GET /internal/products/{id}/ownership-check`` (params: ``user_id``) returns
``200`` with body ``{"category_id": "<uuid>"}`` on success (it previously
returned an empty/opaque 200), and ``404`` (``catalog.product.not_found``) when
the product does not exist / is not owned / is soft-deleted.  The 404 conflation
(not-found ≡ cross-tenant ≡ soft-deleted) is the §10 leak-protection rule,
identical to the monolith ``assert_product_ownership`` semantics.

Both ``assert_product_ownership`` and ``get_category_id`` accept the monolith
call-site signature ``(product_id, user_id, db=db)`` — the ``db`` kwarg is
accepted and IGNORED (the shim talks HTTP, not SQL), so the preserved
``service.py`` call sites are byte-for-byte unchanged.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import MeesellError
from app.core.extracted_clients._transport import request_json


# ── Typed error raised on the monolith's 4xx contract response ──────────────
class ProductNotFoundError(MeesellError):
    """Mirror of ``catalog.exceptions.ProductNotFoundError`` — 404 conflation
    of non-existent + cross-tenant + soft-deleted per §10 leak-protection.

    The monolith ``service.calculate`` raised this from
    ``app.modules.catalog.exceptions`` (service.py:159-160) on the TOCTOU
    soft-delete race; in svc-pricing both the ownership gate and the
    category-id read raise THIS type on a 404 contract response so the error
    envelope is identical.
    """

    code = "catalog.product_not_found"
    status_code = 404
    validation_message_id = "catalog.product.not_found"

    def __init__(self, detail: str = "Product not found.") -> None:
        super().__init__(detail=detail)


# ── Shimmed methods (re-export the catalog_service symbol surface) ──────────
async def assert_product_ownership(
    product_id: UUID,
    user_id: UUID,
    db: Any = None,  # accepted + ignored — HTTP shim (call-site parity)
) -> None:
    """Ownership gate ← ``GET /internal/products/{id}/ownership-check``.

    Returns ``None`` on success (byte-for-byte parity with the monolith
    ``catalog.service.assert_product_ownership`` — service.py:921, used at the
    preserved call sites service.py:134 + :241); raises
    :class:`ProductNotFoundError` when the monolith responds 404 (not owned /
    does not exist / soft-deleted).
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


async def get_category_id(
    product_id: UUID,
    user_id: UUID,
    db: Any = None,  # accepted + ignored — HTTP shim (call-site parity)
) -> UUID:
    """Read the product's ``category_id`` ← the WIDENED
    ``GET /internal/products/{id}/ownership-check`` 200 body (§0.6 Option B).

    REPLACES the monolith's shared-ORM ``db.get(ProductORM, product_id)`` read
    (service.py:151-162).  The same ownership-check endpoint that gates access
    also returns ``{"category_id": "<uuid>"}`` on success — so this call both
    re-asserts ownership AND yields the category needed for the commission
    lookup, in one round-trip.

    Raises :class:`ProductNotFoundError` on a 404 contract response (covers the
    non-existent / cross-tenant / soft-deleted TOCTOU race the monolith guarded
    at service.py:154).
    """
    import httpx

    try:
        payload = await request_json(
            "GET",
            f"/internal/products/{product_id}/ownership-check",
            params={"user_id": str(user_id)},
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise ProductNotFoundError() from exc
        raise

    category_id = (payload or {}).get("category_id")
    if category_id is None:
        # The widened contract guarantees category_id on success; a missing key
        # means the product vanished between gate and read (TOCTOU) — surface
        # the same clean 404 the monolith raised at service.py:154-160.
        raise ProductNotFoundError()
    return UUID(str(category_id))


__all__ = [
    "ProductNotFoundError",
    "assert_product_ownership",
    "get_category_id",
]
