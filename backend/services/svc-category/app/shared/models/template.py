"""Template ORM model — per-schema Meesho category templates (vendored).

Table: ``category.templates`` (Sub-Plan F schema-split, migration
``c4f1e7a9d302``).

Mirrors the monolith ``app.shared.models.template.Template`` (MVP_ARCH §2.3 +
§5.6.1 + §5.5.13 + §12.6), bound to the ``category`` Postgres schema.  The
intra-schema ``categories`` relationship is KEPT (categories + templates move
together).

``schema_jsonb`` carries the §5A.B compiled wizard schema envelope that
svc-category serves verbatim via ``fetch_schema`` (the §F4 frozen shim #1).
``compliance_shape`` is materialised as the §5A.B 7th envelope key at read
time in ``repository.fetch_schema_uncached``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base

if TYPE_CHECKING:
    from app.shared.models.category import Category


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    # SHA-256 of canonical schema — used for deduplication at seed time.
    # 3,557 distinct templates serve 3,772 leaves.
    schema_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="SHA-256 of canonical schema JSON for deduplication",
    )
    # Full per-field schema (display + canonical + export layers).
    # See §5.6.1 for complete shape.
    schema_jsonb: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    # Compliance representation for the Export Adapter (§5.5.13 + §12.6).
    # 'standard'  → 9 separate fields → 9 XLSX columns (3,771/3,772 leaves).
    # 'collapsed' → 9 fields concatenated → 3 XLSX columns (Eye-Serum only).
    compliance_shape: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default=text("'standard'"),
        comment="standard | collapsed — selects Export Adapter compliance strategy",
    )
    parsed_from_xlsx_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    parser_version: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        server_default=text("'0.2'"),
        comment="meesell-xlsx-parser version that produced this template",
    )

    # Intra-schema relationship (categories + templates move together).
    categories: Mapped[list[Category]] = relationship(
        "Category",
        back_populates="template",
    )

    # Table-level DDL
    __table_args__ = (
        CheckConstraint(
            "compliance_shape IN ('standard', 'collapsed')",
            name="ck_templates_compliance_shape",
        ),
        {"schema": "category"},
    )
