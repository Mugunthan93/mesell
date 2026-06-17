"""Audit event ORM model — vendored for svc-export, bound to ``public``.

Mirrors the monolith ``app.shared.models.audit_event.AuditEvent`` column
shape (MVP_ARCH §10 / §11.2) but drops the ``User`` relationship (svc-export
only INSERTs; it never traverses the relationship).

CROSS-SCHEMA INSERT (spec §3.A)
-------------------------------
The export Celery task writes ``export.completed`` / ``export.failed`` rows
to ``public.audit_events`` — a cross-schema write from the svc-export
service whose own table (``exports``) lives in the ``export`` schema.  This
model is explicitly bound to ``public`` so the INSERT lands in the
monolith-owned audit table, NOT a phantom ``export.audit_events``.
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
    # Bound to public — the monolith owns this table; export writes into it
    # cross-schema (its own table lives in the ``export`` schema).
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
