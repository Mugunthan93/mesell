"""Category ORM model — 3,772 Meesho leaf nodes (vendored for svc-category).

Table: ``category.categories`` (Sub-Plan F schema-split, migration
``c4f1e7a9d302`` — ``ALTER TABLE public.categories SET SCHEMA category``).

Mirrors the monolith ``app.shared.models.category.Category`` column shape
(MVP_ARCH §2.3) with two vendoring deltas:

* Bound to the ``category`` Postgres schema via ``{"schema": "category"}`` —
  svc-category OWNS these tables post-extraction.
* The cross-schema ``products`` + ``catalogs`` relationships are DROPPED:
  those tables are catalog-owned (still in ``public`` / future ``catalog``
  schema) and are NOT vendored into this service.  svc-category never
  traverses them.  The intra-schema ``template`` + ``field_enum_values``
  relationships are KEPT (all three tables move together).

The pg_trgm GIN indexes (idx_categories_path_trgm / leaf_name_trgm /
super_name_trgm) survive ``SET SCHEMA`` and are re-declared here so
autogenerate does not emit false-positive drop-index drift.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base

if TYPE_CHECKING:
    from app.shared.models.template import Template
    from app.shared.models.field_enum_value import FieldEnumValue


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    # Meesho's own numeric leaf ID, e.g. "10003".  Unique globally.
    meesho_leaf_id: Mapped[str] = mapped_column(
        String(16),
        unique=True,
        nullable=False,
        comment="Meesho's own leaf node ID, e.g. '10003'",
    )
    super_id: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        comment="Meesho super-category ID, e.g. '11' = Women Fashion",
    )
    super_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Meesho super-category display name",
    )
    # Full breadcrumb path — trigram-indexed in migration §7.4.
    path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full breadcrumb path — trigram-indexed for browse search",
    )
    leaf_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Terminal category name — trigram-indexed for prefix/fuzzy search",
    )
    # FK to templates (many-to-one) — intra-schema (category.templates).
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("category.templates.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Template this leaf maps to (shared among leaves with identical schemas)",
    )
    # Meesho commission percentage for this leaf (seeded from parsed data where available)
    commission_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Intra-schema relationships only (Product / Catalog relationships DROPPED —
    # those tables are catalog-owned and not vendored into svc-category).
    template: Mapped[Template] = relationship(
        "Template",
        back_populates="categories",
    )
    field_enum_values: Mapped[list[FieldEnumValue]] = relationship(
        "FieldEnumValue",
        back_populates="category",
        cascade="all, delete-orphan",
    )

    # B-tree indexes per §2.3 DDL.
    # GIN trigram indexes per §7.4 DDL — created by migration a1b2c3d4e5f6
    # using CREATE INDEX CONCURRENTLY, then moved with the table by
    # ``SET SCHEMA category`` (migration c4f1e7a9d302).  Declared here so
    # autogenerate does not report them missing and emit false-positive
    # drop_index() calls.
    __table_args__ = (
        Index("idx_categories_super", "super_id"),
        Index("idx_categories_template", "template_id"),
        Index("idx_categories_meesho_leaf", "meesho_leaf_id"),
        Index(
            "idx_categories_path_trgm",
            "path",
            postgresql_using="gin",
            postgresql_ops={"path": "gin_trgm_ops"},
        ),
        Index(
            "idx_categories_leaf_name_trgm",
            "leaf_name",
            postgresql_using="gin",
            postgresql_ops={"leaf_name": "gin_trgm_ops"},
        ),
        Index(
            "idx_categories_super_name_trgm",
            "super_name",
            postgresql_using="gin",
            postgresql_ops={"super_name": "gin_trgm_ops"},
        ),
        {"schema": "category"},
    )
