"""Field enum value ORM model — per-(category, field_name) enum storage.

Table: ``field_enum_values``
DDL source: MVP_ARCHITECTURE §2.3 + §5.6.4

Schema delta applied (pre-approved by coordinator):
  - ``enum_entries JSONB`` (richer structure) replaces the simpler
    ``enum_values JSONB`` (plain string array) from §2.3.
    Shape per §5.6.4:
      [
        {"canonical": "Cotton", "meesho": "Cotton",   "labels": {"en": "Cotton"}},
        {"canonical": "Silk",   "meesho": "Silk",     "labels": {"en": "Silk"}},
        ...
      ]
    For most enums: canonical == meesho == labels.en (V1).
    For codified enums (e.g. "PE-HD"): labels.en has a friendly name.
    Export Adapter writes ``meesho`` to XLSX.
    Frontend renders ``labels[locale]``.
    AI auto-fill reasons in ``canonical``.

Covers the 291 "Brand-pattern" fields (same field name, different enum source
per category) and all other category-specific enum fields.

PK: composite (category_id, field_name).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKeyConstraint, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.category import Category


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

    # Relationship
    category: Mapped[Category] = relationship(
        "Category",
        back_populates="field_enum_values",
    )

    # Table-level DDL
    __table_args__ = (
        ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            ondelete="CASCADE",
            name="fk_field_enum_values_category_id",
        ),
        Index("idx_field_enum_value_count", "value_count"),
    )
