"""Audit event ORM model — vendored for svc-customer, bound to ``public``.

Mirrors the monolith ``app.shared.models.audit_event.AuditEvent`` column shape
(MVP_ARCH §10 / §11.2) but drops the ``User`` relationship (svc-customer only
INSERTs; it never traverses the relationship).

Bound to ``public`` (spec §3.A)
-------------------------------
The vendored ``audit_mw`` writes the request-level audit fact to
``public.audit_events`` cross-schema.  customer's 3 PATCH endpoints carry
``@audit_event(...)`` → an INSERT lands in ``public.audit_events`` (shared,
INSERT-only).  The model is bound to ``public`` so the write lands in the
monolith-owned audit table, NOT a phantom ``customer.audit_events``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Identity, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"
    # Bound to public — the monolith owns this table; customer writes into it
    # cross-schema (INSERT-only; customer's owned schema is `customer`).
    __table_args__ = (
        Index("idx_audit_user_time", "user_id", "occurred_at"),
        Index("idx_audit_entity", "entity_type", "entity_id"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        comment="BIGSERIAL — monotonic, append-only, not UUID",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )
    entity_type: Mapped[str | None] = mapped_column(String(20))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    diff_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    metadata_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
