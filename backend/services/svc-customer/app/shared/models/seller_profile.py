"""Seller profile ORM model — svc-customer OWNED table, bound to ``customer``.

Table: ``customer.seller_profile``
DDL source: MVP_ARCHITECTURE §2.2 + §12.6 (vendored from the monolith
``app.shared.models.seller_profile``).

Schema-split + FK severance (MS-E Risk #5 — spec §3.A)
------------------------------------------------------
The table was moved ``public`` → ``customer`` by migration ``a9f3b2c5e1d8``.
The cross-schema FK ``fk_seller_profile_user_id`` (``seller_profile.user_id``
→ ``public.users.id``) was DROPPED, and the ORM-level
``relationship("User", ...)`` was REMOVED.  In svc-customer the model is a
plain UUID PK with NO ``ForeignKeyConstraint`` and NO ``relationship`` —
user-identity is verified at the application layer via JWT
(``core/auth.get_current_user``), NOT a SQL FK.

The GIN index ``idx_seller_profile_super_cats`` on ``active_super_categories``
is KEPT — it followed the table on ``SET SCHEMA`` (PostgreSQL moves
table-owned indexes automatically) and is declared here so the ORM matches the
live DDL.

Original monolith deltas (still apply)
--------------------------------------
  - The 3 collapsed "details" fields (manufacturer_details, packer_details,
    importer_details) from the §2.2 DDL are DROPPED per §12.6 — only the 9
    standard individual fields are stored.
  - ``onboarding_complete`` aligns with MEESHO_CATEGORY_INTELLIGENCE §3 naming.

All timestamps are TIMESTAMPTZ.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Index, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base


class SellerProfile(Base):
    __tablename__ = "seller_profile"

    # PK: plain UUID — NO FK to public.users (severed on extraction, Risk #5).
    # One-to-one with users is enforced at the application layer via JWT.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment="User this profile belongs to (1-1 with users; FK severed on extraction)",
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

    # ── Table-level DDL ───────────────────────────────────────────────────
    # NO ForeignKeyConstraint — the cross-schema FK to public.users was severed
    # on extraction (Risk #5).  GIN index is KEPT (followed the table on the
    # SET SCHEMA move).  Bound to the `customer` schema.
    __table_args__ = (
        # GIN index for array containment queries on active_super_categories.
        # e.g. WHERE active_super_categories @> '{26}'
        Index(
            "idx_seller_profile_super_cats",
            "active_super_categories",
            postgresql_using="gin",
        ),
        {"schema": "customer"},
    )
