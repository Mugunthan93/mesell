"""Catalog ORM model — user catalog container.

Table: ``catalogs``
DDL source: MVP_ARCHITECTURE §2.4 + §10.2

A catalog groups one or more products under a single Meesho upload batch.
``user_id`` FK is indexed for tenant isolation queries (§10.2 mandate).
``category_id`` FK is nullable — the category may be set at catalog creation
or deferred until the first product is added.

Indexes per §10.10 multi-tenancy checklist.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.category import Category
    from app.models.product import Product


class Catalog(Base):
    __tablename__ = "catalogs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Tenant owner",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Optional FK to categories — may be set at catalog creation or refined per-product.
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'draft'"),
        comment="draft | submitted | exported",
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
    user: Mapped[User] = relationship(
        "User",
        back_populates="catalogs",
    )
    category: Mapped[Category | None] = relationship(
        "Category",
        back_populates="catalogs",
    )
    products: Mapped[list[Product]] = relationship(
        "Product",
        back_populates="catalog",
        cascade="all, delete-orphan",
    )

    # Indexes per §10.10
    __table_args__ = (
        Index("idx_catalogs_user", "user_id"),
        Index("idx_catalogs_user_created", "user_id", "created_at"),
        Index("idx_catalogs_category_id", "category_id"),
    )
