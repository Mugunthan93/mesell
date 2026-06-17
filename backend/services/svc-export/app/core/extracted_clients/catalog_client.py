"""catalog-svc HTTP shim — re-exports the ``catalog_service`` symbol surface.

Shims 2 of the 6 cross-module methods export consumes (spec §0.4):

* :func:`assert_product_ownership` ← catalog/service.py:919
  → ``GET /internal/products/{id}/ownership-check`` (raises
  :class:`ProductNotFoundError` on 404).
* :func:`get_product_for_export` ← catalog/service.py:943
  → ``GET /internal/products/{id}/export-snapshot`` (returns the frozen
  :class:`ExportSnapshotInternal` shape).

Both accept the monolith call-site signature ``(product_id, user_id, db=db)``
— the ``db`` kwarg is accepted and IGNORED (the shim talks HTTP, not SQL), so
``service.py`` call sites are byte-for-byte unchanged.

The deserialization targets (:class:`ExportSnapshotInternal` /
:class:`ValidationSummaryInternal`) mirror ``catalog/domain.py:130-162`` field
shape so the export pipeline's attribute access
(``snapshot.validation_summary.status`` / ``snapshot.category_id`` /
``snapshot.fields`` / ``snapshot.ai_suggestions`` / ``snapshot.image_refs``)
is identical to the in-process version.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.errors import MeesellError
from app.core.extracted_clients._transport import request_json


# ── Deserialization targets (mirror catalog/domain.py shapes) ───────────────
@dataclass(frozen=True)
class ValidationSummaryInternal:
    """Mirror of ``catalog.domain.ValidationSummaryInternal`` (the subset the
    export pipeline reads — only ``status`` is consumed by ``initiate_export``).
    """

    status: str
    product_id: UUID | None = None
    compulsory_filled: int | None = None
    compulsory_total: int | None = None
    optional_filled: int | None = None
    optional_total: int | None = None
    has_validation_errors: bool | None = None


@dataclass(frozen=True)
class ExportSnapshotInternal:
    """Mirror of ``catalog.domain.ExportSnapshotInternal``.

    ``image_refs`` are GCS object paths (NOT signed URLs — the export pipeline
    issues fresh signed URLs itself).
    """

    product_id: UUID
    category_id: UUID
    fields: dict[str, Any]
    ai_suggestions: dict[str, Any]
    image_refs: tuple[str, ...]
    validation_summary: ValidationSummaryInternal


# ── Typed errors raised on the monolith's 4xx contract responses ────────────
class ProductNotFoundError(MeesellError):
    """Mirror of ``catalog.exceptions.ProductNotFoundError`` — 404 conflation
    of non-existent + cross-tenant per §4.C.
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


async def get_product_for_export(
    product_id: UUID,
    user_id: UUID,
    db: Any = None,  # accepted + ignored — HTTP shim (call-site parity)
) -> ExportSnapshotInternal:
    """Export snapshot ← ``GET /internal/products/{id}/export-snapshot``.

    Deserializes the monolith JSON into the frozen :class:`ExportSnapshotInternal`.
    """
    import httpx

    try:
        payload = await request_json(
            "GET",
            f"/internal/products/{product_id}/export-snapshot",
            params={"user_id": str(user_id)},
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise ProductNotFoundError() from exc
        raise

    vs = payload.get("validation_summary") or {}
    return ExportSnapshotInternal(
        product_id=UUID(str(payload["product_id"])),
        category_id=UUID(str(payload["category_id"])),
        fields=dict(payload.get("fields") or {}),
        ai_suggestions=dict(payload.get("ai_suggestions") or {}),
        image_refs=tuple(payload.get("image_refs") or ()),
        validation_summary=ValidationSummaryInternal(
            status=str(vs.get("status", "")),
            product_id=(
                UUID(str(vs["product_id"])) if vs.get("product_id") else None
            ),
            compulsory_filled=vs.get("compulsory_filled"),
            compulsory_total=vs.get("compulsory_total"),
            optional_filled=vs.get("optional_filled"),
            optional_total=vs.get("optional_total"),
            has_validation_errors=vs.get("has_validation_errors"),
        ),
    )


__all__ = [
    "ExportSnapshotInternal",
    "ProductNotFoundError",
    "ValidationSummaryInternal",
    "assert_product_ownership",
    "get_product_for_export",
]
