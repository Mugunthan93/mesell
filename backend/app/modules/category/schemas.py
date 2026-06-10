"""``category`` module Pydantic v2 schemas — BACKEND_ARCHITECTURE.md §9.E (LOCKED 2026-06-05).

10 request/response models per §9.E verbatim.

FieldSpec note
--------------
``app.i18n.schema_contract.FieldSpec`` is a ``typing.TypedDict``; Pydantic v2
on Python < 3.12 requires ``typing_extensions.TypedDict`` for nested-TypedDict
schema generation.  Following the precedent set in
``app.modules.customer.schemas`` (2026-06-07 session), ``SchemaResponse.fields``
is typed as ``list[dict[str, Any]]`` at the Pydantic layer.
``test_per_field_shape_keys.py`` is the schema-conformance gate for the 9
§5A.C-locked per-field keys.  When the runtime moves to 3.12 (or i18n switches
to ``typing_extensions.TypedDict``), this can be replaced with
``list[FieldSpec]``.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# Request models
# ─────────────────────────────────────────────────────────────────────────────


class SuggestQuery(BaseModel):
    """Query parameters for GET /api/v1/categories/suggest.

    ``q`` must have 1–500 non-empty characters (after strip).  Pydantic
    enforces the character bounds; the service layer enforces the
    strip-and-recheck rule.

    validation_message_id on violation: ``validation.suggest_q.too_short_or_long``
    """

    q: str = Field(min_length=1, max_length=500)


class BrowseQuery(BaseModel):
    """Query parameters for GET /api/v1/categories/browse.

    All four params are optional on the wire; defaults apply when absent.

    validation_message_id on pagination violation:
    ``validation.browse.invalid_pagination``
    """

    q: str | None = Field(default=None, max_length=100)
    super_id: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


# ─────────────────────────────────────────────────────────────────────────────
# Smart Picker response  (§9.B.1)
# ─────────────────────────────────────────────────────────────────────────────


class CategorySuggestion(BaseModel):
    """One ranked category suggestion from the Smart Category Picker.

    ``confidence`` is calibrated by ``picker.calibrate_confidence``
    (range 0.0–1.0).  ``reasons`` are short human-readable rationale
    strings produced by the AI-track ranking pipeline.
    """

    category_id: UUID
    super_id: str
    super_name: str
    path: str
    leaf_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str]


class SuggestResponse(BaseModel):
    """Response envelope for GET /api/v1/categories/suggest.

    ``fallback_offered=True`` signals the frontend to surface the manual
    /browse fallback per ``MVP_ARCH §5.1`` decision #8.  Always 200 — never
    a 5xx for AI failures per §9.B.1 graceful-fallback contract.
    """

    suggestions: list[CategorySuggestion] = Field(max_length=5)
    fallback_offered: bool


# ─────────────────────────────────────────────────────────────────────────────
# Browse response  (§9.B.2)
# ─────────────────────────────────────────────────────────────────────────────


class BrowseResultRow(BaseModel):
    """One result row from the pg_trgm browse search.

    ``similarity`` is the pg_trgm score 0.0–1.0.  In V1 the repository
    reports 0.0 (ordering is preserved by the SQL ORDER BY); lifting the
    score end-to-end is a V1.5 refinement.

    Reused inside ``SuperCategoryNode.leaves`` for the tree endpoint
    (``similarity`` is 0.0 in tree mode — not computed).
    """

    category_id: UUID
    super_id: str
    super_name: str
    path: str
    leaf_name: str
    similarity: float


class BrowseResponse(BaseModel):
    """Paginated response for GET /api/v1/categories/browse."""

    results: list[BrowseResultRow]
    total: int
    limit: int
    offset: int


# ─────────────────────────────────────────────────────────────────────────────
# Category Tree response  (§9.B.3)
# ─────────────────────────────────────────────────────────────────────────────


class SuperCategoryNode(BaseModel):
    """One super-category bucket in the full hierarchical tree.

    ``leaves`` reuse ``BrowseResultRow`` (similarity is 0.0 in tree mode).
    """

    super_id: str
    super_name: str
    leaves: list[BrowseResultRow]


class CategoryTreeResponse(BaseModel):
    """Response envelope for GET /api/v1/categories (full tree)."""

    super_categories: list[SuperCategoryNode]


# ─────────────────────────────────────────────────────────────────────────────
# Schema response  (§9.B.4 — pass-through of templates.schema_jsonb)
# ─────────────────────────────────────────────────────────────────────────────


class SchemaResponse(BaseModel):
    """Pass-through of ``templates.schema_jsonb`` envelope per §5A.B.

    ``extra='allow'`` ensures forward-compatible envelope evolutions
    (§5A amendments) do not break existing readers.

    ``fields`` is typed as ``list[dict[str, Any]]`` following the precedent
    in ``app.modules.customer.schemas`` — see module docstring for the
    Python 3.11 TypedDict rationale.  ``test_per_field_shape_keys.py`` is
    the conformance gate for the 9 §5A.C-locked per-field keys.

    ``main_sheet_label`` is the Meesho header consumed by the export adapter
    (§14 / M10).  It is present in this response because the export path
    needs it; the seller-facing wizard does NOT render this field.
    """

    model_config = ConfigDict(extra="allow")

    fields: list[dict[str, Any]]
    compulsory_count: int
    optional_count: int
    total_count: int
    wizard_step_count: int
    main_sheet_label: str
    compliance_shape: Literal["standard", "collapsed"]


# ─────────────────────────────────────────────────────────────────────────────
# Field-Enum response  (§9.B.5)
# ─────────────────────────────────────────────────────────────────────────────


class EnumEntry(BaseModel):
    """One enum entry from ``field_enum_values``.

    ``canonical`` — the canonical internal value used by the catalog
    validator for input acceptance.

    ``meesho`` — the Meesho-format string consumed ONLY by the export
    adapter (§14 / M10); never rendered in the seller wizard.

    ``labels`` — ``{locale: localised_label}``; V1 contains only ``"en"``.
    """

    canonical: str
    meesho: str
    labels: dict[str, str]


class FieldEnumResponse(BaseModel):
    """Response envelope for GET /api/v1/categories/{id}/field-enum/{name}."""

    enum_entries: list[EnumEntry]
    total: int
    truncated: bool


# ─────────────────────────────────────────────────────────────────────────────
# Public surface
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Request
    "BrowseQuery",
    "SuggestQuery",
    # Suggest
    "CategorySuggestion",
    "SuggestResponse",
    # Browse
    "BrowseResultRow",
    "BrowseResponse",
    # Tree
    "CategoryTreeResponse",
    "SuperCategoryNode",
    # Schema
    "SchemaResponse",
    # Field-Enum
    "EnumEntry",
    "FieldEnumResponse",
]
