"""WebhookEvent ORM model — Razorpay webhook idempotency + audit + replay store.

Table: ``webhook_events``
DDL source: RAZORPAY_INTEGRATION_SPEC §7.3.

Design points:
  - **String primary key (NOT UUID).**  ``event_id`` is a Razorpay-issued string
    (e.g. ``"event_XXXXXXXXXXXXXXXX"``).  This is intentional: the dedupe gate
    uses ``INSERT ... ON CONFLICT (event_id) DO NOTHING``, which requires
    ``event_id`` to be the conflict target (a PK or UNIQUE constraint).  Using the
    natural Razorpay event id as PK avoids a separate UNIQUE index and makes the
    conflict target unambiguous.  This is the ONLY model in this wave that does NOT
    use a UUID PK.
  - No ``user_id`` FK — a webhook transport record has no inherent user.  The business
    effect (plan grant, audit event) lands in ``audit_events`` in later waves with a
    real ``user_id``.  Clean separation: ``webhook_events`` = transport record,
    ``audit_events`` = business effect.
  - ``payload_jsonb`` stores the FULL raw webhook payload.  This was the column V1
    lacked (V1's ``capture_razorpay_webhook`` only logged event keys).  Storing the
    full payload enables **replay**: a buggy handler version can be fixed and events
    reprocessed from our own store without re-fetching from Razorpay (§4.4).
  - ``signature_valid`` is recorded for ops triage — lets ops distinguish "arrived but
    had bad sig" from "arrived and processed" from "arrived but handler errored".
  - No relationships — ``webhook_events`` is a standalone audit/idempotency store.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base


class WebhookEvent(Base):
    """Razorpay webhook event transport record.

    Written atomically with the event handler's state mutation inside one transaction.
    On conflict (duplicate ``event_id``), the ``INSERT ... ON CONFLICT DO NOTHING``
    dedupe gate returns immediately without re-processing (§4.2).
    """

    __tablename__ = "webhook_events"

    # ── Primary key — STRING, not UUID (see module docstring) ───────────────
    event_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        comment=(
            "Razorpay event id — natural string PK used as the ON CONFLICT dedupe key.  "
            "Not a UUID.  See RAZORPAY_INTEGRATION_SPEC §7.3."
        ),
    )

    # ── Event classification ─────────────────────────────────────────────────
    event_type: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        comment="Razorpay event type, e.g. subscription.charged, payment.captured",
    )

    # ── Payload ──────────────────────────────────────────────────────────────
    payload_jsonb: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment=(
            "Full raw webhook payload — enables replay of processed events "
            "without re-fetching from Razorpay (RAZORPAY_INTEGRATION_SPEC §4.4).  "
            "Note: may contain PII (customer email/phone); apply retention/purge policy."
        ),
    )

    # ── Signature verification result ────────────────────────────────────────
    signature_valid: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment=(
            "HMAC-SHA256 signature verified against RAZORPAY_WEBHOOK_SECRET at receipt time.  "
            "False = arrived but signature failed (logged for ops; Razorpay will retry)."
        ),
    )

    # ── Processing lifecycle ──────────────────────────────────────────────────
    received_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        comment="Wall-clock time the HTTP request was received by our webhook endpoint",
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="NULL until the event handler commits successfully; set in the same tx",
    )
    processing_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Last handler error message — used for ops triage of stuck events",
    )

    # ── Indexes ──────────────────────────────────────────────────────────────
    __table_args__ = (
        # Event-type + time: "show me all subscription.charged events in the last 7 days"
        Index("idx_webhook_events_type_received", "event_type", "received_at"),
        # Partial index on unprocessed events: fast sweep for stuck/pending events.
        # processed_at IS NULL = not yet handled or handler rolled back.
        Index(
            "idx_webhook_events_unprocessed",
            "processed_at",
            postgresql_where=text("processed_at IS NULL"),
        ),
    )
