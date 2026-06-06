"""Product image ORM model.

Table: ``product_images``
DDL source: MVP_ARCHITECTURE §2.5

Corpus invariant (MEESHO_CATEGORY_INTELLIGENCE §8): image rules are 100%
uniform across all 3,772 Meesho leaves — 4 slots, slot 1 (front) compulsory.
No per-category variation is ever needed.

Key design:
  - ``order_idx`` CHECK (1..4) — enforced at DB level.
  - ``is_front`` is a GENERATED ALWAYS AS (order_idx = 1) STORED column,
    mapped via SQLAlchemy ``Computed(persisted=True)``.
  - UNIQUE(product_id, order_idx) prevents duplicate slot assignments.
  - ``precheck_jsonb`` stores the image pre-check pipeline results.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Computed, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base

if TYPE_CHECKING:
    from app.shared.models.product import Product


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    gcs_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="GCS object path: {user_id}/{product_id}/{order_idx}.jpg",
    )
    # 1 = front (compulsory), 2–4 = additional (optional).
    order_idx: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="1 (front/compulsory) to 4 (optional) — CHECK 1..4 enforced",
    )
    # GENERATED ALWAYS AS (order_idx = 1) STORED in DDL.
    # Computed(persisted=True) maps PostgreSQL GENERATED ALWAYS AS ... STORED.
    # SQLAlchemy will not attempt to INSERT/UPDATE this column.
    is_front: Mapped[bool] = mapped_column(
        Boolean,
        Computed("order_idx = 1", persisted=True),
        comment="GENERATED ALWAYS AS (order_idx = 1) STORED",
    )
    # Image metadata populated by the pre-check pipeline.
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    color_space: Mapped[str | None] = mapped_column(
        String(8),
        comment="RGB | CMYK | L (greyscale)",
    )
    # Pre-check results from the image pipeline (Pillow + Gemini watermark check).
    precheck_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'pending'"),
        comment="pending | processing | ready | failed",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationship
    product: Mapped[Product] = relationship(
        "Product",
        back_populates="images",
    )

    # Table-level DDL
    __table_args__ = (
        UniqueConstraint("product_id", "order_idx", name="uq_product_images_product_order"),
        CheckConstraint(
            "order_idx BETWEEN 1 AND 4",
            name="ck_product_images_order_idx",
        ),
        Index("idx_product_images_product_id", "product_id"),
    )
