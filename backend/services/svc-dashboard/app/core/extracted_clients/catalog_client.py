"""catalog-svc HTTP shim — re-exports the ``catalog_service`` symbol surface.

Shims the 1 cross-module method dashboard consumes from catalog (spec §0.4):

* :func:`list_products` ← catalog/service.py:999
  → ``GET /internal/products?page={page}&limit={limit}`` (returns the frozen
  :class:`PaginatedProductsInternal` shape).

The call site is byte-for-byte preserved (``dashboard/service.py:78``)::

    await catalog_service.list_products(user_id=user_id, pagination=pagination, db=db)

so :func:`list_products` accepts ``user_id`` + ``pagination`` + ``db`` exactly.
``db`` is accepted and IGNORED (the shim talks HTTP, not SQL).  ``user_id`` is
NOT placed in the URL: the callee derives the tenant from the forwarded JWT
``sub`` claim — the same ``scope_to_user(user_id)`` the in-process
``catalog_repo.list_paginated`` enforces per §10.D (frozen contract,
SUB_PLAN_0B §"Shim 1").  The kwarg is accepted purely for call-site parity.

The deserialization targets (:class:`Product` / :class:`Pagination` /
:class:`PaginatedProductsInternal`) mirror ``catalog/domain.py:35 / :219 / :170``
field shape so dashboard's ``_compose_response`` attribute access
(``product.id`` / ``.name`` / ``.category_id`` / ``.status`` / ``.created_at``
/ ``.updated_at`` and ``paginated.items`` / ``.total`` / ``.page`` / ``.limit``)
is identical to the in-process version.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from app.core.errors import MeesellError
from app.core.extracted_clients._transport import request_json

# Mirror of ``catalog.domain.ProductStatus`` (catalog/domain.py:31).
ProductStatus = Literal["draft", "ready"]


# ── Deserialization targets (mirror catalog/domain.py shapes) ───────────────
@dataclass(frozen=True, kw_only=True)
class Product:
    """Mirror of ``catalog.domain.Product`` (catalog/domain.py:35).

    The full row shape is carried for fidelity; dashboard's
    ``_compose_response`` only reads ``id`` / ``name`` / ``category_id`` /
    ``status`` / ``created_at`` / ``updated_at``.
    """

    id: UUID
    user_id: UUID
    catalog_id: UUID
    category_id: UUID
    name: str | None
    status: ProductStatus
    fields: dict[str, Any]
    ai_suggestions: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


@dataclass(frozen=True, kw_only=True)
class Pagination:
    """Mirror of ``catalog.domain.Pagination`` (catalog/domain.py:219).

    Built by dashboard's router from :class:`schemas.DashboardQuery` and passed
    through to :func:`list_products` — its ``page`` / ``limit`` become the
    query params on the internal request.
    """

    page: int = 1
    limit: int = 20


@dataclass(frozen=True, kw_only=True)
class PaginatedProductsInternal:
    """Mirror of ``catalog.domain.PaginatedProductsInternal`` (catalog/domain.py:170).

    Consumed by ``dashboard.service`` cross-module — list/page result.
    """

    items: tuple[Product, ...]
    total: int
    page: int
    limit: int


# ── Typed error raised on the monolith's 4xx contract response ──────────────
class ProductNotFoundError(MeesellError):
    """Mirror of ``catalog.exceptions.ProductNotFoundError`` — 404 conflation
    of non-existent + cross-tenant per §4.C.

    NOTE: dashboard's ``list_products`` never 404s on empty inventory (empty
    list is a valid 200 — first-time-seller state per SUB_PLAN_0B §"Shim 1").
    This type exists for shim-contract parity with the catalog ``/internal/*``
    error surface.
    """

    code = "catalog.product_not_found"
    status_code = 404
    validation_message_id = "catalog.product.not_found"

    def __init__(self, detail: str = "Product not found.") -> None:
        super().__init__(detail=detail)


def _parse_dt(value: Any) -> datetime:
    """Parse an ISO-8601 timestamp string (or pass a datetime through)."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _parse_dt_opt(value: Any) -> datetime | None:
    """Parse an optional ISO-8601 timestamp (``None`` passes through)."""
    if value is None:
        return None
    return _parse_dt(value)


def _hydrate_product(raw: dict[str, Any]) -> Product:
    """Hydrate one :class:`Product` from the frozen internal JSON shape."""
    return Product(
        id=UUID(str(raw["id"])),
        user_id=UUID(str(raw["user_id"])),
        catalog_id=UUID(str(raw["catalog_id"])),
        category_id=UUID(str(raw["category_id"])),
        name=raw.get("name"),
        status=raw["status"],
        fields=dict(raw.get("fields") or {}),
        ai_suggestions=dict(raw.get("ai_suggestions") or {}),
        created_at=_parse_dt(raw["created_at"]),
        updated_at=_parse_dt(raw["updated_at"]),
        deleted_at=_parse_dt_opt(raw.get("deleted_at")),
    )


# ── Shimmed method (re-export the catalog_service symbol surface) ───────────
async def list_products(
    *,
    user_id: UUID,  # accepted for call-site parity; tenant derived from JWT (frozen contract)
    pagination: Pagination,
    db: Any = None,  # accepted + ignored — HTTP shim (call-site parity)
) -> PaginatedProductsInternal:
    """Paginated active products ← ``GET /internal/products?page=&limit=``.

    The user JWT (forwarded by ``_transport`` from the request context)
    resolves the tenant on the callee side — ``user_id`` is NOT placed in the
    URL (frozen contract, SUB_PLAN_0B §"Shim 1").  Deserializes the monolith
    JSON into the frozen :class:`PaginatedProductsInternal`.
    """
    payload = await request_json(
        "GET",
        "/internal/products",
        params={"page": pagination.page, "limit": pagination.limit},
    )

    items = tuple(_hydrate_product(item) for item in (payload.get("items") or ()))
    return PaginatedProductsInternal(
        items=items,
        total=int(payload["total"]),
        page=int(payload["page"]),
        limit=int(payload["limit"]),
    )


__all__ = [
    "PaginatedProductsInternal",
    "Pagination",
    "Product",
    "ProductNotFoundError",
    "ProductStatus",
    "list_products",
]
