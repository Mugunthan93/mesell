"""``export`` Pydantic v2 wire models per §14.G — PLACEHOLDER for api-routes-builder.

HAND-OFF NOTE (spec §3.B)
-------------------------
The authoritative ``schemas.py`` + ``router.py`` are delivered by
meesell-api-routes-builder in Phase B (near-parallel, once the service-method
signatures froze — which they have, here).  This file is provided by
services-builder ONLY so that the byte-for-byte ``service.py``
(``from app.schemas import ExportInitiatedResponse, ExportResponse``) is
importable and unit-testable NOW.  The wire shapes below are vendored verbatim
from the monolith ``app.modules.export.schemas`` (§14.G LOCKED) — if
api-routes-builder re-authors this file, it MUST keep these two response shapes
identical so ``service.py`` is unaffected.

M10 enforcement (§14.J): ``meesho_column_header`` / ``meesho_column_index`` /
``enum_codes_map`` NEVER appear in any wire model — that is the schema-layer
M10 boundary.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExportRequest(BaseModel):
    """POST /products/{id}/export-xlsx body."""

    model_config = ConfigDict(extra="forbid")

    format: Literal["xlsx_only", "xlsx_with_images"] = "xlsx_with_images"


class ExportInitiatedResponse(BaseModel):
    """POST /products/{id}/export-xlsx 202 response per §14.B.1."""

    export_id: UUID
    status: Literal["pending"]
    enqueued_task_id: str
    initiated_at: datetime


class ExportResponse(BaseModel):
    """GET /exports/{id} 200 response per §14.B.2."""

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
    """Wire shape for the OPTIONAL cross-module dashboard.summary surface."""

    product_id: UUID
    latest_export_id: UUID | None = None
    latest_export_status: Literal["pending", "ready", "failed"] | None = None
    latest_completed_at: datetime | None = None


__all__ = [
    "ExportRequest",
    "ExportInitiatedResponse",
    "ExportResponse",
    "ExportStatusSummaryResponse",
]
