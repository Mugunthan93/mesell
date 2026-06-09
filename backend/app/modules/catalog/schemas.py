"""``catalog`` Pydantic v2 request/response models.

Per BACKEND_ARCHITECTURE.md §10.E (LOCKED 2026-06-05).

Request models use ``model_config = ConfigDict(extra="forbid")`` — typos
surface at the API edge as 400 ``validation.body.unknown_key`` via
:class:`app.core.errors._pydantic_validation_handler`.

Response models use ``model_config = ConfigDict(extra="ignore",
from_attributes=True)`` — forward-compat + accepts both dataclass and
ORM instances for ``model_validate`` at the router boundary.

12 models total per §10.E::

  CreateProductRequest, PatchProductRequest, AutofillRequest         (requests)
  ProductResponse, AutofillSuggestion, AutofillResponse,
  ProductPreviewField, ProductPreviewResponse,
  ProductDraftResponse, Pagination, PaginatedProductsResponse,
  ValidationSummary, ExportSnapshot                                  (responses)

All UUIDs serialise as strings per Pydantic v2 default; all datetimes
are ISO-8601 with TZ per `CLAUDE.md` ("TIMESTAMPTZ for all timestamps").
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# Request — create product
# ─────────────────────────────────────────────────────────────────────────────
class CreateProductRequest(BaseModel):
    """POST /api/v1/products body per §10.B.1.

    * ``catalog_id`` ``None`` → service creates a default-named catalog
      (``"{seller_phone_last4}-Drafts-{YYYYMMDD-HHMM}"``).  Non-null →
      product is added to the existing catalog (404 if not owned).
    * ``name`` is the seller-visible product name; ``None`` lets the
      wizard default to "Untitled product".
    """

    model_config = ConfigDict(extra="forbid")

    catalog_id: UUID | None = None
    category_id: UUID
    name: str | None = Field(default=None, max_length=200)


# ─────────────────────────────────────────────────────────────────────────────
# Request — patch product (fields + optional status transition)
# ─────────────────────────────────────────────────────────────────────────────
class PatchProductRequest(BaseModel):
    """PATCH /api/v1/products/{id} body per §10.B.2.

    * ``fields`` is a partial JSON patch — keys are canonical field names
      per ``templates.schema_jsonb.fields[*].canonical_name`` (§5A.C
      regex ``[a-z][a-z0-9_]*``), values are primitive payloads per the
      field's ``primitive`` (§5A.D).
    * ``status`` is the optional state transition: omit to leave
      unchanged; ``"ready"`` triggers full-schema completeness validation;
      ``"draft"`` is the explicit revert.

    At least one of ``fields`` / ``status`` MUST be present — the
    validator below rejects empty bodies with 400.
    """

    model_config = ConfigDict(extra="forbid")

    fields: dict[str, Any] | None = None
    status: Literal["draft", "ready"] | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "PatchProductRequest":
        """Reject empty bodies (both ``fields`` and ``status`` unset).

        Surfaces as ``validation.body.unknown_key`` via the §4.F handler
        chain — the chain treats Pydantic ValueError raises as 422 with
        a dynamic id; the catch-all phrasing is preserved.
        """
        if self.fields is None and self.status is None:
            raise ValueError(
                "PatchProductRequest must set at least one of 'fields' or 'status'"
            )
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Request — autofill
# ─────────────────────────────────────────────────────────────────────────────
class AutofillRequest(BaseModel):
    """POST /api/v1/products/{id}/autofill body per §10.B.3.

    * ``description`` 1..2000 chars per §10.E.
    * ``fields_to_fill`` optional allowlist of canonical names — default
      ``None`` lets the AI fill all empty compulsory fields it has
      confidence in.
    """

    model_config = ConfigDict(extra="forbid")

    description: str = Field(..., min_length=1, max_length=2000)
    fields_to_fill: list[str] | None = Field(default=None, max_length=50)


# ─────────────────────────────────────────────────────────────────────────────
# Response — product
# ─────────────────────────────────────────────────────────────────────────────
class ProductResponse(BaseModel):
    """201 / 200 response across §10.B.1 + §10.B.2 + §10.B.3.

    ``fields`` mirrors ``products.fields_jsonb``;
    ``ai_suggestions`` mirrors ``products.ai_suggestions_jsonb``.
    """

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: UUID
    catalog_id: UUID
    category_id: UUID
    name: str | None
    status: Literal["draft", "ready"]
    fields: dict[str, Any]
    ai_suggestions: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Response — autofill
# ─────────────────────────────────────────────────────────────────────────────
class AutofillSuggestion(BaseModel):
    """One field's AI suggestion per `MVP_ARCH §2.4` shape."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    value: Any
    confidence: float = Field(..., ge=0.0, le=1.0)
    source: Literal["ai"] = "ai"


class AutofillResponse(BaseModel):
    """200 response for §10.B.3.

    Always HTTP 200 — even when ``fallback_offered=True`` (§9.B.1 +
    §6A.F precedent: budget exhaustion does NOT 503).
    """

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    suggestions: dict[str, AutofillSuggestion]
    applied: dict[str, bool]
    fallback_offered: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Response — live preview
# ─────────────────────────────────────────────────────────────────────────────
class ProductPreviewField(BaseModel):
    """One row of the §10.B.4 preview composite."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    canonical_name: str
    display_label: str
    value: Any
    is_advanced: bool


class ProductPreviewResponse(BaseModel):
    """200 response for §10.B.4.

    ``fields`` is ordered per the schema's wizard-step composition (§5A.C).
    ``compliance`` is the standard 9-key shape per §5A.F + V1 universal
    collection rule (collapsed-shape transform happens in §14 export).
    """

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: UUID
    name: str | None
    category_path: str
    fields: list[ProductPreviewField]
    image_urls: list[str]
    compliance: dict[str, Any]
    status: Literal["draft", "ready"]


# ─────────────────────────────────────────────────────────────────────────────
# Response — draft recovery
# ─────────────────────────────────────────────────────────────────────────────
class ProductDraftResponse(BaseModel):
    """200 response for §10.B.6 (204 when no draft — empty body).

    DECISION FLAG §10-CATALOG-D1 (applied):
        ``last_updated`` ← ``product_drafts.saved_at``.
        ``fields`` ← ``draft_jsonb["fields"]`` (wrapper).
        ``autosave_count`` ← ``draft_jsonb["autosave_count"]``.

    Legacy rows without the wrapper key coerce to
    ``autosave_count=1`` and ``fields=<draft_jsonb>``.
    """

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    fields: dict[str, Any]
    last_updated: datetime
    autosave_count: int


# ─────────────────────────────────────────────────────────────────────────────
# Pagination — for the list_products cross-module surface
# ─────────────────────────────────────────────────────────────────────────────
class Pagination(BaseModel):
    """Offset pagination per §10.E.

    Bounded ``limit`` to keep dashboard pages responsive.
    """

    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class PaginatedProductsResponse(BaseModel):
    """Cross-module response shape for the dashboard's product list."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    items: list[ProductResponse]
    total: int
    page: int
    limit: int


# ─────────────────────────────────────────────────────────────────────────────
# ValidationSummary — cross-module read for the dashboard badge
# ─────────────────────────────────────────────────────────────────────────────
class ValidationSummary(BaseModel):
    """Output of :func:`catalog.service.get_validation_summary` — dashboard
    status-badge math.

    Recomputed against the schema each call — small N (the dashboard
    page-size is bounded).
    """

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    product_id: UUID
    compulsory_filled: int
    compulsory_total: int
    optional_filled: int
    optional_total: int
    has_validation_errors: bool
    status: Literal["draft", "ready"]


# ─────────────────────────────────────────────────────────────────────────────
# ExportSnapshot — cross-module return for export.service
# ─────────────────────────────────────────────────────────────────────────────
class ExportSnapshot(BaseModel):
    """Frozen view consumed by §14 export.

    ``image_refs`` are GCS object paths (NOT signed URLs — export issues
    fresh signed URLs itself).
    """

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    product_id: UUID
    category_id: UUID
    fields: dict[str, Any]
    ai_suggestions: dict[str, Any]
    image_refs: list[str]
    validation_summary: ValidationSummary


__all__ = [
    "AutofillRequest",
    "AutofillResponse",
    "AutofillSuggestion",
    "CreateProductRequest",
    "ExportSnapshot",
    "PaginatedProductsResponse",
    "Pagination",
    "PatchProductRequest",
    "ProductDraftResponse",
    "ProductPreviewField",
    "ProductPreviewResponse",
    "ProductResponse",
    "ValidationSummary",
]
