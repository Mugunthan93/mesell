"""Product image ORM model — vendored for svc-image, bound to schema ``image``.

Mirrors the monolith ``app.shared.models.product_image.ProductImage`` column
shape (MVP_ARCH §2.5) but:

1. binds to the ``image`` Postgres schema via
   ``__table_args__ = (..., {"schema": "image"})`` — Sub-Plan C schema-split.
   A1's migration (PR #200) moved ``public.product_images`` →
   ``image.product_images`` (``ALTER TABLE product_images SET SCHEMA image``).
2. DROPS the ``product_id`` ForeignKey to ``products`` AND the
   ``relationship("Product")`` — OPTION B (spec §0.3): svc-image issues NO
   ``products`` read and the table now lives in a different schema than
   ``products`` (catalog-owned, → schema ``catalog`` at MS-5).  The
   ``product_id`` is a plain UUID column; tenancy is proved by the upstream
   ``catalog.assert_product_ownership`` HTTP shim, not an FK / ORM traversal.

DDL source: MVP_ARCHITECTURE §2.5.  Corpus invariant
(MEESHO_CATEGORY_INTELLIGENCE §8): image rules are 100% uniform across all
3,772 Meesho leaves — 4 slots, slot 1 (front) compulsory.

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

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    # OPTION B: plain UUID — NO ForeignKey to products (cross-schema, no read).
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Catalog-owned product UUID — tenancy via assert_product_ownership shim",
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

    # Table-level DDL — bound to the ``image`` schema (Sub-Plan C split).
    __table_args__ = (
        UniqueConstraint("product_id", "order_idx", name="uq_product_images_product_order"),
        CheckConstraint(
            "order_idx BETWEEN 1 AND 4",
            name="ck_product_images_order_idx",
        ),
        Index("idx_product_images_product_id", "product_id"),
        {"schema": "image"},
    )
