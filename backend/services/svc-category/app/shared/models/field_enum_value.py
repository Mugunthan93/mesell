"""Field enum value ORM model — per-(category, field_name) enum (vendored).

Table: ``category.field_enum_values`` (Sub-Plan F schema-split, migration
``c4f1e7a9d302``).

Mirrors the monolith ``app.shared.models.field_enum_value.FieldEnumValue``
(MVP_ARCH §2.3 + §5.6.4), bound to the ``category`` Postgres schema.  Covers
the 291 "Brand-pattern" enum blobs svc-category serves via ``get_field_enum``
(the §F4 frozen shim #2, single-flight per §6.8).

PK: composite (category_id, field_name).  The FK to ``category.categories``
is intra-schema (both tables move together).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKeyConstraint, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base

if TYPE_CHECKING:
    from app.shared.models.category import Category


class FieldEnumValue(Base):
    __tablename__ = "field_enum_values"

    # Composite PK
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment="FK to categories — enum values are per-category",
    )
    field_name: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
        comment="Canonical field name (normalised via field_aliases)",
    )

    # Richer enum structure per §5.6.4.
    # Each entry: {"canonical": "...", "meesho": "...", "labels": {"en": "..."}}
    enum_entries: Mapped[list | dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Richer enum structure per §5.6.4",
    )
    # Materialised count — avoids jsonb_array_length on the hot query path.
    value_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="len(enum_entries) — materialised for query speed",
    )
    # True when value_count reflects the FULL list but enum_entries stores only
    # a sample.  Used for large enums (Brand, Compatible Models) where
    # API-backed search (dropdown_api_search primitive) is required.
    truncated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="TRUE if stored enum_entries are a sample of a larger set",
    )

    # Intra-schema relationship.
    category: Mapped[Category] = relationship(
        "Category",
        back_populates="field_enum_values",
    )

    # Table-level DDL — FK is intra-schema (category.categories).
    __table_args__ = (
        ForeignKeyConstraint(
            ["category_id"],
            ["category.categories.id"],
            ondelete="CASCADE",
            name="fk_field_enum_values_category_id",
        ),
        Index("idx_field_enum_value_count", "value_count"),
        {"schema": "category"},
    )
