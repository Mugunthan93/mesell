"""Audit event ORM model — append-only audit log.

Table: ``audit_events``
DDL source: MVP_ARCHITECTURE §10 / §11.2

Key design points:
  - BIGSERIAL primary key (NOT UUID) — append-only, high-volume table.
    Expected ~3,000 rows/day after coalescing; ~1.1M rows/year at 1,000 sellers.
    BIGSERIAL avoids UUID generation overhead and keeps the PK monotonically
    ordered (aids heap-scans ordered by time).
    Implemented via ``BigInteger + Identity(always=True)`` (PostgreSQL 10+
    GENERATED ALWAYS AS IDENTITY — equivalent to BIGSERIAL, SQL-standard).
  - ``user_id`` FK is RESTRICT (not CASCADE) — audit records must survive
    user deletion for compliance/legal purposes.
  - ``diff_jsonb`` stores before/after delta using canonical field names only
    (never Meesho column headers — CORE_PHILOSOPHY F8).  PII fields are
    scrubbed before insertion (see §11.9).
  - NO UPDATE, NO DELETE path in application code.  Archive-and-purge
    (Celery beat task, 90-day hot retention) is the only lifecycle operation.

Indexes per §11.2:
  - idx_audit_user_time  (user_id, occurred_at) — Pattern B queries
  - idx_audit_entity     (entity_type, entity_id) — Pattern A queries
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Identity, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuditEvent(Base):
    __tablename__ = "audit_events"

    # BIGSERIAL: BigInteger + Identity(always=True) → GENERATED ALWAYS AS IDENTITY
    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        comment="BIGSERIAL — monotonic, append-only, not UUID",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        comment="product.patch | product.export | seller_profile.update | auth.login",
    )
    entity_type: Mapped[str | None] = mapped_column(
        String(20),
        comment="product | seller_profile | user — NULL for auth.login",
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        comment="ID of the affected entity — NULL for auth.login",
    )
    # Before/after delta.  NULL for events with no field delta (e.g. auth.login).
    # Only changed fields are stored.  Canonical names only, PII scrubbed.
    diff_jsonb: Mapped[dict | None] = mapped_column(
        JSONB,
        comment="{before: {...}, after: {...}} — canonical field names only, PII scrubbed",
    )
    # Request context: IP, user_agent, request_id, session_id.
    metadata_jsonb: Mapped[dict | None] = mapped_column(
        JSONB,
        comment="Request context: ip, user_agent, request_id, session_id",
    )
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # RESTRICT means audit records survive user deletion.
    user: Mapped[User] = relationship(
        "User",
        back_populates="audit_events",
    )

    # Indexes per §11.2 — two primary query patterns
    __table_args__ = (
        # Pattern B: "show all activity for user X in the last N days"
        Index("idx_audit_user_time", "user_id", "occurred_at"),
        # Pattern A: "what changed on this entity between time A and B"
        Index("idx_audit_entity", "entity_type", "entity_id"),
    )
