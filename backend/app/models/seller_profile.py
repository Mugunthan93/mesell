"""Seller profile ORM model — Onboarding compliance bucket.

Table: ``seller_profile``
DDL source: MVP_ARCHITECTURE §2.2 + §12.6

Schema deltas applied (pre-approved by coordinator):
  - The 3 collapsed "details" fields (manufacturer_details, packer_details,
    importer_details) from the §2.2 DDL are DROPPED per §12.6 final ruling.
    Only the 9 standard individual fields are stored here.  The Export Adapter
    concatenates them to 3 combined Eye-Serum columns at XLSX export time only.
  - ``onboarding_complete`` aligns with MEESHO_CATEGORY_INTELLIGENCE §3 naming.

``user_id`` is both primary key and foreign key (one-to-one with users).
All timestamps are TIMESTAMPTZ.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKeyConstraint, Index, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class SellerProfile(Base):
    __tablename__ = "seller_profile"

    # PK == FK: one-to-one with users
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment="User this profile belongs to (1-1 with users)",
    )

    # ── 9-field Legal Metrology compliance block ──────────────────────────
    # Present in 3,771/3,772 Meesho categories (near-universal; treated as
    # universal in V1).
    manufacturer_name: Mapped[str] = mapped_column(Text, nullable=False)
    manufacturer_address: Mapped[str] = mapped_column(Text, nullable=False)
    manufacturer_pincode: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
        comment="6-digit Indian PIN code",
    )
    packer_name: Mapped[str] = mapped_column(Text, nullable=False)
    packer_address: Mapped[str] = mapped_column(Text, nullable=False)
    packer_pincode: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
        comment="6-digit Indian PIN code",
    )
    # Importer fields are optional — many domestic sellers are also importer
    importer_name: Mapped[str | None] = mapped_column(Text)
    importer_address: Mapped[str | None] = mapped_column(Text)
    importer_pincode: Mapped[str | None] = mapped_column(
        String(6),
        comment="6-digit Indian PIN code",
    )

    # ── Universal base field ──────────────────────────────────────────────
    country_of_origin: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default=text("'India'"),
    )

    # ── Conditional compliance extensions (per super-category) ───────────
    # Keyed by Meesho super_id string.  Example:
    #   {"26": {"fssai_license_number": "10012345678901",
    #           "fssai_expiry": "2027-12-31"},
    #    "13": {"bis_isi_certification_number": "IS-1234-2024"}}
    compliance_extensions: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    # ── Active super-categories ───────────────────────────────────────────
    # Which Meesho super-categories this seller sells in.
    # Drives which onboarding extension steps appear in the wizard.
    active_super_categories: Mapped[list] = mapped_column(
        ARRAY(String),
        nullable=False,
        server_default=text("'{}'::text[]"),
    )

    # ── Onboarding gate ───────────────────────────────────────────────────
    onboarding_complete: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment="True once all compulsory base fields are filled",
    )

    # ── Bookkeeping ───────────────────────────────────────────────────────
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

    # ── Relationship ──────────────────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User",
        back_populates="seller_profile",
    )

    # ── Table-level DDL ───────────────────────────────────────────────────
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_seller_profile_user_id",
        ),
        # GIN index for array containment queries on active_super_categories.
        # e.g. WHERE active_super_categories @> '{26}'
        Index(
            "idx_seller_profile_super_cats",
            "active_super_categories",
            postgresql_using="gin",
        ),
    )
