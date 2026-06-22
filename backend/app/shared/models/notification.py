"""Notification ORM model — idempotent, channel-agnostic change alerts.

Table: ``notifications``
DDL source: RETENTION_CATEGORY_MONITOR.md §4.3

Design rules:
    - Idempotent fan-out: UNIQUE on ``(user_id, category_id, content_hash)``
      named ``uq_notification_user_cat_hash``.  Fan-out workers INSERT ON
      CONFLICT DO NOTHING so retries never double-notify.
    - Channel-agnostic: NO ``channel`` column.  V1.x delivers via in-app bell
      only; email/WhatsApp are additive channels gated by feature flags that
      the worker layer resolves — the model must not bake any channel.
    - ``is_read`` / ``read_at``: user-facing read state; ``idx_notification_user_unread``
      on ``(user_id, is_read)`` powers the bell unread-count query.

``payload_jsonb`` holds the human-readable diff summary and the list of
affected catalog/product IDs, assembled by the fan-out worker.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base

if TYPE_CHECKING:
    from app.shared.models.user import User
    from app.shared.models.category import Category


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Seller this notification targets",
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        comment="Category whose change triggered this notification",
    )
    # The content_hash from the category_snapshot row that caused this notification.
    # Combined with (user_id, category_id) forms the idempotency key.
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Hash of the snapshot that triggered this notification — part of idempotency key",
    )
    # Human-readable diff summary + affected catalog/product list assembled by fan-out worker.
    # Shape: {summary: str, diff_dimensions: [...], affected_catalog_ids: [...]}
    payload_jsonb: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="Diff summary payload for the in-app bell",
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment="User has dismissed/read this notification",
    )
    read_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Timestamp when the user read the notification, NULL if unread",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        foreign_keys=[user_id],
    )
    category: Mapped[Category] = relationship(
        "Category",
        foreign_keys=[category_id],
    )

    __table_args__ = (
        # Idempotency constraint — fan-out uses ON CONFLICT DO NOTHING.
        UniqueConstraint(
            "user_id",
            "category_id",
            "content_hash",
            name="uq_notification_user_cat_hash",
        ),
        # Bell unread-count query: SELECT COUNT(*) WHERE user_id=X AND is_read=false.
        Index("idx_notification_user_unread", "user_id", "is_read"),
    )
