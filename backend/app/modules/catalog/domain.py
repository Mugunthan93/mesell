"""``catalog`` internal domain types — frozen dataclasses per §10.F.

Per BACKEND_ARCHITECTURE.md §10.F (LOCKED 2026-06-05).

These types never cross the HTTP boundary directly — the Pydantic
schemas in :mod:`.schemas` are the wire shapes.  Using ``frozen=True``
+ ``kw_only=True`` keeps them immutable and safer to pass between
service-layer helpers.

Cross-module exports (consumed via ``from app.modules.catalog import
domain as catalog_domain``):

* :class:`Product`                  — image / pricing / dashboard / export
* :class:`ExportSnapshotInternal`   — export consumes this verbatim
* :class:`ValidationSummaryInternal`— dashboard consumes this verbatim
* :class:`PaginatedProductsInternal`— dashboard consumes this verbatim

Conversion between ORM ↔ domain happens at the repository boundary
(:mod:`.repository`).  Routers never see ORM instances; they map domain
objects to the Pydantic response shapes in :mod:`.schemas`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

# Re-exported for type-hint convenience inside catalog/.
ProductStatus = Literal["draft", "ready"]


@dataclass(frozen=True, kw_only=True)
class Product:
    """Mirrors a ``products`` row; never crosses HTTP.

    ``deleted_at`` is exposed on the domain object even though every
    public service surface filters it out — exposure is for the
    repository / soft-delete debug path only.  Consumers must NOT use a
    product with ``deleted_at != None``.
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
class Catalog:
    """Mirrors a ``catalogs`` row; never crosses HTTP."""

    id: UUID
    user_id: UUID
    name: str
    created_at: datetime


@dataclass(frozen=True, kw_only=True)
class ProductDraft:
    """Mirrors a ``product_drafts`` row — autosave snapshot.

    DECISION FLAG §10-CATALOG-D1 (applied per master ruling 2026-06-07)
    ------------------------------------------------------------------
    The ``product_drafts`` table per migration ``935e55b4852c`` carries
    columns ``(user_id, product_id, draft_jsonb, saved_at)``.  §10.D
    contract requires ``fields``, ``last_updated``, ``autosave_count``.
    Wrapped envelope shape inside ``draft_jsonb``::

        draft_jsonb = {"fields": <merged_fields_dict>,
                       "autosave_count": <int>}

    The repository unwraps on read; legacy rows without the wrapper key
    coerce to ``autosave_count=1`` and ``fields=<draft_jsonb>``.
    """

    user_id: UUID
    product_id: UUID
    fields: dict[str, Any]
    last_updated: datetime
    autosave_count: int


@dataclass(frozen=True, kw_only=True)
class AutofillSuggestionInternal:
    """One field's AI suggestion + confidence + provenance.

    Per `MVP_ARCH §2.4` ``ai_suggestions_jsonb`` shape: each entry is
    ``{"value", "confidence", "source"}``.  V1 ``autofill.v1`` prompt
    outputs ``{"fields": {<canonical>: <value>}}`` flat — the §10.B.3
    flow assigns a single high-confidence value to every emitted field
    (the prompt instructs the model to OMIT fields it is not confident
    about — see §10.B.3 step 7).  The locked confidence floor for
    auto-application is **0.85** per `MVP_ARCH §5.2`; emitted-with-
    omission semantics map to 0.9 (above the floor → auto-applied).
    """

    canonical_name: str
    value: Any
    confidence: float
    source: Literal["ai"]


@dataclass(frozen=True, kw_only=True)
class AutofillResponse:
    """Service-layer return shape — mirrored to
    :class:`schemas.AutofillResponse` at the router boundary.

    ``suggestions``: full AI output (the per-field provenance map).
    ``applied``: which canonical_names were merged into
                  ``products.fields_jsonb`` (confidence ≥ 0.85).
    ``fallback_offered``: True when AI was skipped or exhausted —
                            §6A.F + §9.B.1 precedent (200, not 503).
    """

    suggestions: dict[str, AutofillSuggestionInternal]
    applied: dict[str, bool]
    fallback_offered: bool


@dataclass(frozen=True, kw_only=True)
class ValidationSummaryInternal:
    """Consumed by :func:`catalog.service.get_validation_summary` — the
    dashboard's status-badge math.

    All counts are computed against the per-category schema envelope at
    each call (small N — dashboard page size bounded).
    """

    product_id: UUID
    compulsory_filled: int
    compulsory_total: int
    optional_filled: int
    optional_total: int
    has_validation_errors: bool
    status: ProductStatus


@dataclass(frozen=True, kw_only=True)
class ExportSnapshotInternal:
    """Consumed by ``export.service`` cross-module (per §16) — frozen
    view of a product at the moment of export.

    Snapshot semantics: export builds the XLSX from this fixed view.
    ``image_refs`` are GCS object paths (NOT signed URLs — the export
    pipeline issues fresh signed URLs itself).
    """

    product_id: UUID
    category_id: UUID
    fields: dict[str, Any]
    ai_suggestions: dict[str, Any]
    image_refs: tuple[str, ...]
    validation_summary: ValidationSummaryInternal


@dataclass(frozen=True, kw_only=True)
class PaginatedProductsInternal:
    """Consumed by ``dashboard.service`` cross-module — list/page result."""

    items: tuple[Product, ...]
    total: int
    page: int
    limit: int


@dataclass(frozen=True, kw_only=True)
class PreviewField:
    """One row of the §10.B.4 live-preview composite.

    ``canonical_name``: backend-internal key from
        ``products.fields_jsonb`` per §5A.C.
    ``display_label``: localised display string from
        ``templates.schema_jsonb.fields[*].name`` per §5A.C + §5A.I.
    ``value``: as-stored field value (no Meesho transformation — that
        happens in §14 export only).
    ``is_advanced``: True for V1's ``group_id`` only (per §5A.F + §12.4).
    """

    canonical_name: str
    display_label: str
    value: Any
    is_advanced: bool


@dataclass(frozen=True, kw_only=True)
class ProductPreviewInternal:
    """Service-layer return shape for §10.B.4 — mirrored to
    :class:`schemas.ProductPreviewResponse` at the router boundary.

    ``compliance`` is the §5A.F shape (standard or collapsed) from
    ``customer.service.get_compliance_block`` (V1: V1 emits a 9-key
    standard block universally — the export Adapter does the collapsed-
    shape transformation; preview shows the standard block).
    """

    id: UUID
    name: str | None
    category_path: str
    fields: tuple[PreviewField, ...]
    image_urls: tuple[str, ...]
    compliance: dict[str, Any]
    status: ProductStatus


@dataclass(frozen=True, kw_only=True)
class Pagination:
    """Pagination input for :func:`catalog.service.list_products`.

    Matches :class:`schemas.Pagination`; carried as a frozen dataclass
    so the service surface is HTTP-shape-free for cross-module callers
    that compose pages without going through the router (dashboard).
    """

    page: int = 1
    limit: int = 20


__all__ = [
    "AutofillResponse",
    "AutofillSuggestionInternal",
    "Catalog",
    "ExportSnapshotInternal",
    "PaginatedProductsInternal",
    "Pagination",
    "PreviewField",
    "Product",
    "ProductDraft",
    "ProductPreviewInternal",
    "ProductStatus",
    "ValidationSummaryInternal",
]
