"""Template ORM model — per-schema storage for Meesho category templates.

Table: ``templates``
DDL source: MVP_ARCHITECTURE §2.3 + §5.6.1 + §5.5.13 + §12.6

Schema delta applied (pre-approved by coordinator):
  - ``compliance_shape VARCHAR(10) NOT NULL DEFAULT 'standard'`` added per
    §5.5.13 and §12.6.  CHECK constraint: ('standard', 'collapsed').
    'standard' covers 3,771/3,772 categories.  'collapsed' is the Eye-Serum
    leaf only.  The Export Adapter reads this flag to select the compliance
    strategy (StandardComplianceStrategy vs CollapsedComplianceStrategy).

``schema_jsonb`` shape (per §5.6.1):
  {
    "fields": [
      {
        "canonical_name": "...",       // primary key (canonical layer)
        "data_type": "text|number|dropdown|image_url|date|boolean",
        "primitive": "<one of 11>",
        "marker": "compulsory|optional",
        "is_advanced": false,
        "is_hidden": false,
        "compliance_role": null,       // null | manufacturer_name | packer_address | ...
        "step_id": "basics|pricing|...",
        "max_length": N,
        "min_length": N,
        "regex": "...",
        "min_value": N,
        "max_value": N,
        "unit_suffix": "...",
        "display_label": {"en": "..."},        // display layer
        "display_help": {"en": "..."},
        "display_placeholder": {"en": "..."},
        "display_unit_label": {"en": "..."},
        "validation_message": {"en": "..."},
        "help_url": null,
        "meesho_column_header": "...", // export layer
        "meesho_column_index": N,
        "meesho_default": null,
        "enum_codes_map": null,
        "enum_labels": null
      }
    ],
    "compulsory_count": N,
    "optional_count": N,
    "total_count": N,
    "wizard_step_count": N,
    "main_sheet_label": "..."
  }
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.category import Category


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

    # Relationships
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
    )
