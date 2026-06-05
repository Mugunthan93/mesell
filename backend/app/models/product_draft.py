"""Product draft ORM model — autosave crash recovery.

Table: ``product_drafts``
DDL source: MVP_ARCHITECTURE §10 / §11.6

Design:
  - Composite PK (user_id, product_id) — one row per product per user.
  - ``draft_jsonb`` stores the FULL current field state (not a diff).
    On every successful PATCH, the service layer upserts this row via
    ON CONFLICT (user_id, product_id) DO UPDATE.
  - On successful export, the corresponding row is deleted.
  - On browser reload / crash recovery, GET /api/v1/products/{id}/draft
    returns ``draft_jsonb`` to re-hydrate the wizard.

Intentionally separate from audit_events:
  - product_drafts: mutable, low-latency, ephemeral (recovery only).
  - audit_events:   append-only, durable, coalesced (history only).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKeyConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.product import Product


class ProductDraft(Base):
    __tablename__ = "product_drafts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment="Tenant owner (part of composite PK)",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment="Product this draft belongs to (part of composite PK)",
    )
    # Full wizard field state — not a diff.
    draft_jsonb: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Full wizard field state for crash recovery — upserted on every PATCH",
    )
    saved_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        comment="Timestamp of last upsert",
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        back_populates="product_drafts",
    )
    product: Mapped[Product] = relationship(
        "Product",
        back_populates="draft",
        foreign_keys=[product_id],
    )

    # Table-level DDL — two FK constraints + indexes on product_id and saved_at
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_product_drafts_user_id",
        ),
        ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
            name="fk_product_drafts_product_id",
        ),
        Index("idx_product_drafts_product_id", "product_id"),
        # G10 — staleness driver index for TTL cleanup task.
        # Future Celery beat task: DELETE WHERE saved_at < NOW() - INTERVAL '30 days'.
        # Without this index, that query is a full sequential scan.
        Index("idx_product_drafts_saved_at", "saved_at"),
    )
