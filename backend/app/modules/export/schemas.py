"""``export`` module Pydantic v2 wire models per §14.G (LOCKED 2026-06-05).

Wire shapes for the 2 endpoint surfaces:
  1. ``ExportRequest``           — POST /products/{id}/export-xlsx body.
  2. ``ExportInitiatedResponse`` — POST /products/{id}/export-xlsx 202 body.
  3. ``ExportResponse``          — GET /exports/{id} 200 body.
  4. ``ExportStatusSummaryResponse`` — OPTIONAL cross-module surface for V1.5
     dashboard elevation per §14.C (surface exists in V1 but is not consumed).

M10 enforcement (§14.J):
  ``meesho_column_header``, ``meesho_column_index``, and ``enum_codes_map``
  NEVER appear in any of these wire models — that is the schema-layer M10
  boundary per §14.J.  These three symbols belong exclusively to the
  ``domain.py`` / ``service.py`` / ``tasks.py`` internal layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExportRequest(BaseModel):
    """POST /products/{id}/export-xlsx body.

    ``format`` defaults to ``"xlsx_with_images"`` — the primary Feature 9 UX
    (seller downloads sheet + image ZIP in one go).  ``"xlsx_only"`` is the
    V1.5+ bulk-export use case.
    """

    model_config = ConfigDict(extra="forbid")

    format: Literal["xlsx_only", "xlsx_with_images"] = "xlsx_with_images"


class ExportInitiatedResponse(BaseModel):
    """POST /products/{id}/export-xlsx 202 response per §14.B.1."""

    export_id: UUID
    status: Literal["pending"]
    enqueued_task_id: str
    initiated_at: datetime


class ExportResponse(BaseModel):
    """GET /exports/{id} 200 response per §14.B.2.

    Field population rules:
    - ``xlsx_signed_url``: populated when ``status="ready"``.
    - ``zip_signed_url``: populated when ``status="ready"`` AND
      ``format="xlsx_with_images"``.
    - ``error_message`` / ``error_code``: populated when ``status="failed"``.
    - ``completed_at``: always ``None`` in V1 (DDL has no column — D-flag in
      services-builder memory; set at service layer when status="ready"/"failed").
    - ``round_trip_validated``: ``True`` when ``status="ready"`` (MVP_ARCH §5.7
      invariant); ``None`` otherwise.  Derived from status at service layer per D1.
    """

    export_id: UUID
    product_id: UUID
    status: Literal["pending", "ready", "failed"]
    format: Literal["xlsx_only", "xlsx_with_images"]
    xlsx_signed_url: str | None = None
    zip_signed_url: str | None = None
    error_message: str | None = None
    error_code: str | None = None
    initiated_at: datetime
    completed_at: datetime | None = None
    round_trip_validated: bool | None = None


class ExportStatusSummaryResponse(BaseModel):
    """Wire shape for the OPTIONAL cross-module dashboard.summary surface
    per §14.C (V1.5 elevation; surface exists in V1 but is not consumed)."""

    product_id: UUID
    latest_export_id: UUID | None = None
    latest_export_status: Literal["pending", "ready", "failed"] | None = None
    latest_completed_at: datetime | None = None
