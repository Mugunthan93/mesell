"""``monitor`` Pydantic v2 wire schemas — PRIVATE per §16.C Rule 3.

Exposes only the shapes consumed by ``monitor/router.py``.  Nothing outside
the ``monitor`` module imports these schemas.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationItem(BaseModel):
    """Single notification row returned in the list envelope.

    ``payload`` carries the seller-facing diff summary assembled by the
    Wave-4 fan-out worker (shape:
    ``{summary, diff_dimensions, affected_catalog_ids}``).
    ``is_read`` / ``read_at`` expose the bell read-state.  Mark-read mutation
    is deferred to a future wave (Director ruling 2026-06-22).

    ``payload`` is aliased from ``payload_jsonb`` (the ORM column name) so the
    wire API exposes ``payload`` while the ORM attr is ``payload_jsonb``.
    ``populate_by_name=True`` allows the schema to be used with both the ORM
    attr name (from_attributes) and the serialised name (tests / direct init).
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore", populate_by_name=True)

    id: UUID
    category_id: UUID
    content_hash: str
    payload: dict = Field(validation_alias="payload_jsonb")
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Paginated notification list response with additive bell badge.

    ``unread_count`` is additive to the standard ``{data, total, page}``
    envelope — it always reflects the caller's TOTAL unread count (not
    just the current page) so the FE bell badge is accurate regardless of
    the page requested.
    """

    model_config = ConfigDict(extra="ignore")

    data: list[NotificationItem]
    total: int
    page: int
    unread_count: int
