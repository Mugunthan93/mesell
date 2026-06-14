"""Catalog ORM model — vendored for svc-catalog, bound to ``catalog`` schema.

Table: ``catalog.catalogs``
DDL source: MVP_ARCHITECTURE §2.4 + §10.2

The ``catalogs`` table moved ``public`` → ``catalog`` in MS-H Phase A
(migration ``a8f3b2e9c1d5`` — ``ALTER TABLE catalogs SET SCHEMA catalog``).
This vendored model binds ``{"schema": "catalog"}`` explicitly so every
``catalogs`` read/write lands in the owned schema.

Cross-schema FK handling (SUB_PLAN_0H §DB / R6)
----------------------------------------------
* INTRA-schema (both sides in ``catalog``): ``catalogs`` ← ``products`` —
  the ``products.catalog_id → catalog.catalogs.id`` FK object lives on the
  ``Product`` model; the intra-schema ``products`` relationship is KEPT.
* CROSS-schema (``catalog`` → other schemas — valid in PostgreSQL, but NOT
  declared as SQLAlchemy ``ForeignKey``/``relationship`` because the target
  ORM models are sibling-owned and NOT vendored):
    - ``catalogs.user_id → public.users.id`` (→ iam.users) — bare UUID column.
    - ``catalogs.category_id → public.categories.id`` (→ category.categories)
      — bare nullable UUID column.
  The DB-level FK constraints remain in force (preserved by SET SCHEMA); the
  ORM treats these as bare columns.  This is the §2.D "no cross-schema ORM"
  rule at the model layer (mirrors the svc-pricing precedent's
  ``pricing_calc.product_id`` bare-UUID column).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Index, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base

if TYPE_CHECKING:
    from app.shared.models.product import Product


class Catalog(Base):
    __tablename__ = "catalogs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        # NO SQLAlchemy ForeignKey — ``users`` is iam-owned and not vendored.
        # The DB-level cross-schema FK to public.users (→ iam.users) remains in
        # force; the ORM treats this as a bare UUID column (§2.D).
        nullable=False,
        comment="Tenant owner",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Optional cross-schema ref to categories — bare nullable UUID column (the
    # ``categories`` ORM is category-owned and not vendored; DB FK preserved).
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
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

    # Relationships — INTRA-schema only (Catalog ↔ Product, both in ``catalog``).
    # The cross-schema ``user``/``category`` relationships are DROPPED (§2.D).
    products: Mapped[list[Product]] = relationship(
        "Product",
        back_populates="catalog",
        cascade="all, delete-orphan",
    )

    # Indexes per §10.10 + bind the owned ``catalog`` schema (MS-H Phase A).
    __table_args__ = (
        Index("idx_catalogs_user", "user_id"),
        Index("idx_catalogs_user_created", "user_id", "created_at"),
        Index("idx_catalogs_category_id", "category_id"),
        {"schema": "catalog"},
    )
