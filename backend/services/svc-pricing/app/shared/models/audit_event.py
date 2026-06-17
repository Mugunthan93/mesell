"""Audit event ORM model — vendored for svc-pricing, bound to ``public``.

Mirrors the monolith ``app.shared.models.audit_event.AuditEvent`` column
shape (MVP_ARCH §10 / §11.2) but drops the ``User`` relationship (svc-pricing
only INSERTs; it never traverses the relationship).

Bound to ``public`` (spec §3.A + recipe §5)
--------------------------------------------
The vendored ``audit_mw`` writes the request-level audit fact to
``public.audit_events`` cross-schema.  pricing's mounted route is a write
``POST`` (``/products/{id}/price-calc`` with ``@audit_event("pricing.calculated")``)
— so for pricing the audit middleware ACTUALLY FIRES on the 2xx path (unlike
dashboard, whose read-only GET NO-OPs the write-method gate).  ``pricing_calcs``
lives in the ``pricing`` schema; ``audit_events`` lives in ``public`` — so the
audit INSERT is a genuine CROSS-SCHEMA write (the I5 grant on the svc-pricing
role is what makes it land).  The model is bound to ``public`` explicitly so
the write targets the monolith-owned table, NOT a phantom
``pricing.audit_events``.
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
    # Bound to public — the monolith owns this table; pricing writes into it
    # cross-schema (its own subtree owns the ``pricing`` schema, NOT this one).
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
