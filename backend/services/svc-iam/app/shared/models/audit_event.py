"""Audit event ORM model — vendored for svc-iam, bound to ``public``.

Mirrors the monolith ``app.shared.models.audit_event.AuditEvent`` column
shape (MVP_ARCH §10 / §11.2) but drops the ``User`` relationship (svc-iam
only INSERTs; it never traverses the relationship).

Bound to ``public`` (SUB_PLAN_0G §"Code surfaces" + recipe §5)
--------------------------------------------------------------
The vendored ``audit_mw`` (and the §7.I service-layer direct-ORM audit path in
``service.py``, auth-builder's file) writes the request-level audit fact to
``public.audit_events`` cross-schema.  iam's mounted routes are write requests
(``POST /auth/otp/verify``, ``/auth/refresh``, ``/auth/logout``,
``/webhooks/razorpay``) — so for iam the audit path FIRES on the 2xx flow.
``users`` lives in the ``iam`` schema; ``audit_events`` lives in ``public`` —
so the audit INSERT is a genuine CROSS-SCHEMA write (the
``GRANT INSERT ON public.audit_events TO iam_user`` is what makes it land).
The model is bound to ``public`` explicitly so the write targets the
monolith-owned table, NOT a phantom ``iam.audit_events``.

V1 webhook-gap note (SUB_PLAN_0G §0.8 — carried verbatim, NOT fixed)
--------------------------------------------------------------------
``audit_events.user_id`` is NOT NULL.  The Razorpay webhook carries no
``user_id``, so ``service.capture_razorpay_webhook`` (auth-builder's file)
LOGS rather than writing an audit row (returns ``audit_event_id=0``).  This
model is unchanged by that gap — it simply is never INSERTed-into on the
webhook path.  (V1.5 resolution: nullable ``user_id`` or a ``webhook_events``
table.)
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
    # Bound to public — the monolith owns this table; iam writes into it
    # cross-schema (its own subtree owns the ``iam`` schema, NOT this one).
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
