"""Subscription ORM model — billing subscription record.

Table: ``subscriptions``
DDL source: RAZORPAY_INTEGRATION_SPEC §7.1 + §3.1 state table; Pricing v2 §5 tier set.

Design points:
  - ``user_id`` FK is RESTRICT — billing records survive user soft-delete.
  - ``razorpay_subscription_id`` and ``razorpay_order_id`` are both UNIQUE-nullable:
    NULLs are allowed multiple times in Postgres (NULL != NULL in UNIQUE), so LTD rows
    can have NULL in ``razorpay_subscription_id`` and recurring rows can have NULL in
    ``razorpay_order_id`` without violating the constraint.
  - ``current_period_end = NULL`` is the sentinel for "perpetual / LTD".
  - Partial unique index ``uq_subscriptions_one_active_per_user`` prevents a user from
    holding two simultaneous ``status='active'`` subscriptions (e.g. a stale race between
    LTD + recurring paths).  The spec §7.1 explicitly calls for this invariant.
  - ``tier`` CHECK excludes ``free`` — a free user has NO subscriptions row.
    Only ``users.plan`` carries ``free``.
  - ``status`` CHECK mirrors Razorpay's Subscription lifecycle states plus MeeSell's
    ``past_due`` (our name for Razorpay ``pending``).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base

if TYPE_CHECKING:
    from app.shared.models.user import User
    from app.shared.models.payment import Payment


# ---------------------------------------------------------------------------
# Tier + status vocabulary (mirrored in Alembic CHECK constraints)
# ---------------------------------------------------------------------------

#: Allowed values for ``tier`` — the Pricing v2 set MINUS ``free``.
#: A free user has no ``subscriptions`` row at all.
_TIER_VALUES = "('starter','pro','pro_annual','business','business_annual','ltd')"

#: Allowed values for ``status`` — Razorpay lifecycle + MeeSell derivations.
_STATUS_VALUES = (
    "('created','authenticated','active','past_due',"
    "'halted','cancelled','completed','expired')"
)


class Subscription(Base):
    """Recurring subscription or LTD purchase record.

    One row per subscription attempt.  A user may have at most one ``status='active'``
    row at any time (enforced by the partial unique index
    ``uq_subscriptions_one_active_per_user``).  Historical (cancelled/expired) rows
    accumulate for audit purposes.
    """

    __tablename__ = "subscriptions"

    # ── Primary key ─────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # ── Tenant FK ───────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Tenant owner — RESTRICT so billing records survive user soft-delete",
    )

    # ── Razorpay identifiers ─────────────────────────────────────────────────
    razorpay_subscription_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        comment="Razorpay sub id — NULL for LTD Orders path (multiple NULLs allowed)",
    )
    razorpay_order_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        comment="Razorpay order id — set only for LTD one-time purchase",
    )

    # ── Billing attributes ───────────────────────────────────────────────────
    tier: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Pricing v2 tier: starter|pro|pro_annual|business|business_annual|ltd",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment=(
            "Subscription lifecycle status — mirrors Razorpay states + "
            "MeeSell past_due (= Razorpay pending)"
        ),
    )

    # ── Period tracking ──────────────────────────────────────────────────────
    current_period_end: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="End of the current paid period; NULL = perpetual (LTD sentinel)",
    )
    cancel_scheduled_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Set when a cancel-at-cycle-end has been scheduled via Razorpay",
    )

    # ── Timestamps ──────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        onupdate=text("NOW()"),
        comment="Updated by the service layer on every state transition",
    )

    # ── Relationships ────────────────────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User",
        back_populates="subscriptions",
    )
    payments: Mapped[list[Payment]] = relationship(
        "Payment",
        back_populates="subscription",
        foreign_keys="[Payment.subscription_id]",
    )

    # ── Table-level constraints + indexes ────────────────────────────────────
    __table_args__ = (
        # CHECK: tier must be a known non-free billing tier
        CheckConstraint(
            f"tier IN {_TIER_VALUES}",
            name="ck_subscriptions_tier",
        ),
        # CHECK: status must be a known lifecycle value
        CheckConstraint(
            f"status IN {_STATUS_VALUES}",
            name="ck_subscriptions_status",
        ),
        # Hot entitlement lookup: "does user X have an active subscription?"
        Index("idx_subscriptions_user_id_status", "user_id", "status"),
        # Partial unique: at most one 'active' subscription per user.
        # Prevents race conditions where LTD + recurring both land active simultaneously.
        # NULLs in user_id are not possible (NOT NULL column) so the partial index
        # behaves as a true uniqueness guard on active rows only.
        Index(
            "uq_subscriptions_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )
