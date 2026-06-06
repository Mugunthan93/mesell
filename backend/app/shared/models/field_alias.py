"""Field alias ORM model — canonical field-name normalisation map.

Table: ``field_aliases``
DDL source: MVP_ARCHITECTURE §2.3 + §12.2 + MEESHO_CATEGORY_INTELLIGENCE §6

Schema delta applied (pre-approved by coordinator):
  - ``for_xlsx_export BOOLEAN NOT NULL DEFAULT FALSE`` added per §12.2 and
    MEESHO_CATEGORY_INTELLIGENCE §6.
    Rows with for_xlsx_export=TRUE carry a Meesho column header that MUST be
    emitted verbatim (including intentional typos: "Primiary", "Seconadry")
    when generating XLSX.  The Export Adapter queries only these rows to
    build its reverse-alias map.

PK: ``variant_name`` (the raw Meesho string as it appears in XLSX).
16+ confirmed alias families; 23 total families in the seed file.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base


class FieldAlias(Base):
    __tablename__ = "field_aliases"

    # The raw Meesho XLSX column header as-is (may include intentional typos).
    variant_name: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
        comment="Raw Meesho column header — may include intentional typos",
    )
    # Normalised canonical name used internally by all services, AI, and frontend.
    canonical_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Normalised canonical field name for internal use",
    )
    # Origin of this alias entry.
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="'corpus' (auto-detected) | 'manual' (curated by coordinator/founder)",
    )
    # When TRUE, the Export Adapter uses this entry to reverse-map
    # canonical_name → variant_name when writing XLSX.  Typos are intentional
    # and must be preserved to satisfy Meesho's upload validator.
    for_xlsx_export: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment="TRUE → used by Export Adapter to restore Meesho header verbatim",
    )

    # Indexes
    __table_args__ = (
        Index("idx_field_aliases_canonical", "canonical_name"),
        Index("idx_field_aliases_for_export", "for_xlsx_export"),
    )
