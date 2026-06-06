"""Product ORM model — per-product in the catalog wizard.

Table: ``products``
DDL source: MVP_ARCHITECTURE §2.4 + §10.2

Key design points:
  - ``fields_jsonb`` stores seller-filled catalog fields keyed by canonical
    field name.  The backend validates against the category template schema
    on every PATCH.
  - ``ai_suggestions_jsonb`` stores Gemini auto-fill suggestions:
      {"product_name": {"value": "...", "confidence": 0.91,
                        "source": "gemini-2.5-flash", "accepted": true}}
  - ``deleted_at`` is the soft-delete marker (V1 per spec).
  - ``user_id`` is indexed for tenant isolation (§10.2 mandate).
  - Compound index ``(user_id, status)`` for the dashboard list query (§10.10).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base

if TYPE_CHECKING:
    from app.shared.models.catalog import Catalog
    from app.shared.models.user import User
    from app.shared.models.category import Category
    from app.shared.models.product_image import ProductImage
    from app.shared.models.pricing_calc import PricingCalc
    from app.shared.models.export import Export
    from app.shared.models.product_draft import ProductDraft


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalogs.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Tenant owner — every query MUST filter by this column",
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Convenience denormalisation — mirrors the category leaf name for quick display.
    name: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text)

    # Seller-filled catalog fields keyed by canonical field name.
    # Validated against template schema on PATCH.
    fields_jsonb: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    # Gemini auto-fill suggestions (with confidence + source).
    ai_suggestions_jsonb: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'draft'"),
        comment="draft | ready | exported | deleted",
    )
    # Soft delete — NULL means active, timestamp means deleted.
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        comment="Non-NULL → soft-deleted; excluded from active product queries",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    catalog: Mapped[Catalog] = relationship(
        "Catalog",
        back_populates="products",
    )
    user: Mapped[User] = relationship(
        "User",
        back_populates="products",
        foreign_keys=[user_id],
    )
    category: Mapped[Category] = relationship(
        "Category",
        back_populates="products",
    )
    images: Mapped[list[ProductImage]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    pricing_calcs: Mapped[list[PricingCalc]] = relationship(
        "PricingCalc",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    exports: Mapped[list[Export]] = relationship(
        "Export",
        back_populates="product",
    )
    draft: Mapped[ProductDraft | None] = relationship(
        "ProductDraft",
        back_populates="product",
        cascade="all, delete-orphan",
        uselist=False,
    )

    # Indexes per §2.4 DDL + §10.10 multi-tenancy checklist
    __table_args__ = (
        Index("idx_products_user", "user_id"),
        Index("idx_products_category", "category_id"),
        Index("idx_products_status", "status"),
        Index("idx_products_user_status", "user_id", "status"),
        Index("idx_products_catalog_id", "catalog_id"),
    )
