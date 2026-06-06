"""Category ORM model — 3,772 Meesho leaf nodes.

Table: ``categories``
DDL source: MVP_ARCHITECTURE §2.3

Each category maps many-to-one to a template (3,557 distinct templates serve
3,772 leaves — 5.7% deduplication by schema_hash).

B-tree indexes per §2.3 are declared here.  pg_trgm GIN indexes
(idx_categories_path_trgm, idx_categories_leaf_name_trgm,
idx_categories_super_name_trgm) are declared below and were created in
migration a1b2c3d4e5f6 (§7.4) using CONCURRENTLY via autocommit_block().
Both the migration and these ORM declarations must remain in sync so that
``alembic revision --autogenerate`` does not emit false-positive drop-index
operations.
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
    from app.shared.models.product import Product
    from app.shared.models.catalog import Catalog


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
    # FK to templates (many-to-one)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="RESTRICT"),
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

    # Relationships
    template: Mapped[Template] = relationship(
        "Template",
        back_populates="categories",
    )
    field_enum_values: Mapped[list[FieldEnumValue]] = relationship(
        "FieldEnumValue",
        back_populates="category",
        cascade="all, delete-orphan",
    )
    products: Mapped[list[Product]] = relationship(
        "Product",
        back_populates="category",
    )
    catalogs: Mapped[list[Catalog]] = relationship(
        "Catalog",
        back_populates="category",
    )

    # B-tree indexes per §2.3 DDL.
    # GIN trigram indexes per §7.4 DDL — created by migration a1b2c3d4e5f6
    # using CREATE INDEX CONCURRENTLY.  Declared here so that autogenerate
    # does not report them as missing-from-metadata and emit false-positive
    # drop_index() calls in future drift-check revisions.
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
    )
