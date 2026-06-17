"""Product ORM model — vendored for svc-catalog, bound to ``catalog`` schema.

Table: ``catalog.products``
DDL source: MVP_ARCHITECTURE §2.4 + §10.2

The ``products`` table moved ``public`` → ``catalog`` in MS-H Phase A
(migration ``a8f3b2e9c1d5``).  This vendored model binds ``{"schema":
"catalog"}`` explicitly.

Key design points:
  - ``fields_jsonb`` stores seller-filled catalog fields keyed by canonical
    field name.  Validated against the category template schema on PATCH.
  - ``ai_suggestions_jsonb`` stores Gemini auto-fill suggestions.
  - ``deleted_at`` is the soft-delete marker (V1 per spec).
  - ``user_id`` is indexed for tenant isolation (§10.2 mandate).
  - Compound index ``(user_id, status)`` for the dashboard list query (§10.10).

Cross-schema FK handling (SUB_PLAN_0H §DB / R6 — the spine)
---------------------------------------------------------
* INTRA-schema (both sides in ``catalog`` — KEPT as SQLAlchemy FK +
  relationship): ``products.catalog_id → catalog.catalogs.id`` and the
  reverse ``draft`` relationship (``product_drafts.product_id →
  catalog.products.id``).
* CROSS-schema (``catalog`` → other schemas — DB FK preserved but NOT declared
  as SQLAlchemy ``ForeignKey``/``relationship``; the target ORM models are
  sibling-owned and not vendored, §2.D):
    - ``user_id → public.users.id`` (→ iam.users)        — bare UUID column.
    - ``category_id → public.categories.id`` (→ category) — bare UUID column.
  Plus the ``images`` (image-svc), ``pricing_calcs`` (pricing-svc), and
  ``exports`` (export-svc) relationships are DROPPED — those tables live in
  sibling schemas and their ORM models are not vendored here.
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
        # INTRA-schema FK (both sides in ``catalog``) — schema-qualified target.
        ForeignKey("catalog.catalogs.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        # NO SQLAlchemy ForeignKey — ``users`` is iam-owned and not vendored.
        # DB-level cross-schema FK to public.users (→ iam.users) preserved.
        nullable=False,
        comment="Tenant owner — every query MUST filter by this column",
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        # NO SQLAlchemy ForeignKey — ``categories`` is category-owned and not
        # vendored.  DB-level cross-schema FK preserved.
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

    # Relationships — INTRA-schema only.  The cross-schema ``user`` / ``category``
    # / ``images`` / ``pricing_calcs`` / ``exports`` relationships are DROPPED (§2.D).
    catalog: Mapped[Catalog] = relationship(
        "Catalog",
        back_populates="products",
    )
    draft: Mapped[ProductDraft | None] = relationship(
        "ProductDraft",
        back_populates="product",
        cascade="all, delete-orphan",
        uselist=False,
    )

    # Indexes per §2.4 DDL + §10.10 multi-tenancy checklist + owned ``catalog`` schema.
    __table_args__ = (
        Index("idx_products_user", "user_id"),
        Index("idx_products_category", "category_id"),
        Index("idx_products_status", "status"),
        Index("idx_products_user_status", "user_id", "status"),
        Index("idx_products_catalog_id", "catalog_id"),
        {"schema": "catalog"},
    )
