"""Payment ORM model — individual payment / refund record.

Table: ``payments``
DDL source: RAZORPAY_INTEGRATION_SPEC §7.2; founder ruling F9 (amounts in paise).

Design points:
  - ``amount_paise`` stores amounts in Razorpay-native paise (INTEGER).
    F9 ruling: use paise throughout; the ``_paise`` suffix prevents rupees/paise confusion.
    Example: 49900 paise = ₹499.00.
  - ``subscription_id`` is nullable: an LTD payment may have no ``subscriptions`` row yet,
    or a payment record may be written before the subscription is linked.
  - Both ``user_id`` and ``subscription_id`` FK use RESTRICT — payment records survive
    user soft-delete and subscription cancellation (historical billing evidence).
  - ``razorpay_payment_id`` is UNIQUE but nullable — a failed-payment record may exist
    before Razorpay assigns an id.  Multiple NULL values are allowed (NULL != NULL in UNIQUE).
  - ``raw_jsonb`` stores the charge/refund payload slice for ops triage + reconciliation.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base

if TYPE_CHECKING:
    from app.shared.models.user import User
    from app.shared.models.subscription import Subscription


#: Allowed values for ``status``.
_PAYMENT_STATUS_VALUES = "('captured','failed','refunded')"


class Payment(Base):
    """Per-transaction payment or refund record.

    One row per charge attempt or refund event from Razorpay.  Written by the
    webhook handler (Wave 2) when ``subscription.charged`` / ``payment.captured`` /
    ``refund.processed`` events arrive.
    """

    __tablename__ = "payments"

    # ── Primary key ─────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # ── FKs ─────────────────────────────────────────────────────────────────
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="RESTRICT"),
        nullable=True,
        comment=(
            "Parent subscription — nullable for LTD order payments "
            "or pre-linkage failed records"
        ),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Explicit tenant FK — billing records survive user soft-delete (RESTRICT)",
    )

    # ── Razorpay identifier ──────────────────────────────────────────────────
    razorpay_payment_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        comment="Razorpay payment id — nullable (may be absent on failed-before-charge records)",
    )

    # ── Amount ───────────────────────────────────────────────────────────────
    amount_paise: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment=(
            "Amount in paise (Razorpay-native), e.g. 49900 = ₹499.00.  "
            "F9 ruling: always paise, never rupees, never float."
        ),
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        server_default=text("'INR'"),
        comment="ISO 4217 currency code — always INR for V1.5",
    )

    # ── Status ───────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Payment outcome: captured | failed | refunded",
    )

    # ── Event metadata ───────────────────────────────────────────────────────
    event_type: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
        comment=(
            "Source webhook event type, e.g. subscription.charged, "
            "payment.captured, refund.processed"
        ),
    )
    occurred_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Event timestamp from the Razorpay payload (distinct from created_at)",
    )
    raw_jsonb: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Charge or refund payload slice — stored for ops triage + reconciliation",
    )

    # ── Insert timestamp ─────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        comment="Row insert time — distinct from occurred_at (the Razorpay event time)",
    )

    # ── Relationships ────────────────────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User",
        back_populates="payments",
    )
    subscription: Mapped[Subscription | None] = relationship(
        "Subscription",
        back_populates="payments",
        foreign_keys=[subscription_id],
    )

    # ── Table-level constraints + indexes ────────────────────────────────────
    __table_args__ = (
        # CHECK: status must be a known payment outcome
        CheckConstraint(
            f"status IN {_PAYMENT_STATUS_VALUES}",
            name="ck_payments_status",
        ),
        # Tenant-scoped payment history lookup
        Index("idx_payments_user_id", "user_id"),
        # Subscription-scoped payment listing (join from subscriptions)
        Index("idx_payments_subscription_id", "subscription_id"),
    )
