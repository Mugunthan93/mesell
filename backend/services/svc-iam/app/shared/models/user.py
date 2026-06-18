"""User identity ORM model — svc-iam vendored copy.

Table: ``iam.users``  (moved from ``public.users`` by svc-iam migration b1c2d3e4f5a6)
DDL source: MVP_ARCHITECTURE §2.1 + database-builder MEMORY Phase 1

DIFFERENCES FROM MONOLITH app/shared/models/user.py:
  1. ``__table_args__ = {"schema": "iam"}`` — the table is in schema ``iam``, NOT ``public``.
  2. All SQLAlchemy relationships are DROPPED.  iam-svc does not carry the ORM
     models for SellerProfile, Catalog, Product, Export, ProductDraft — those live in their
     own extracted services.  The cross-schema FKs have been dropped by migration
     b1c2d3e4f5a6; ORM relationships would have no backing FK to reference.
  3. ``Base`` is imported from the svc-iam vendored ``app.shared.database`` (NOT the
     monolith's ``app.shared.models.base``).

This vendored copy is the ONLY file that changes between the monolith and iam-svc for
the User model — all other column definitions, server_defaults, types, and indexes
are verbatim.

NOTE: ``core/auth.py`` (also vendored byte-for-byte) performs
``SELECT * FROM users WHERE id = :user_id`` via SQLAlchemy ``select(User)``; it
needs only the ``id``, ``phone``, ``plan`` columns — all present here.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base


class User(Base):
    __tablename__ = "users"
    # google-auth (2026-06-18): table-level CHECK guarantees every row carries
    # at least one authentication identity (phone OR google_sub).  Migration
    # c2d3e4f5a6b7 adds the constraint; it validates immediately on existing
    # rows (all have a phone).  The {"schema": "iam"} dict MUST stay last in
    # the tuple per SQLAlchemy __table_args__ convention.
    __table_args__ = (
        CheckConstraint(
            "phone IS NOT NULL OR google_sub IS NOT NULL",
            name="ck_users_at_least_one_identity",
        ),
        {"schema": "iam"},  # iam-svc: table is in schema 'iam'
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    phone: Mapped[str | None] = mapped_column(
        String(15),
        unique=True,
        nullable=True,  # google-auth: widened NOT NULL → NULL (Google-only users)
        index=True,
        comment="E.164 format Indian mobile; NULL for Google-only users",
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,  # google-auth: now a nullable-UNIQUE linking key
        index=True,
        comment="Verified email; UNIQUE linking key (nullable-unique)",
    )
    google_sub: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True,
        comment="Google Identity Services stable subject (sub); NULL for phone-only users",
    )
    auth_provider: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'phone'"),
        comment="Most-recent provider used to authenticate: phone | google",
    )
    plan: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'free'"),
        index=True,
        comment="free | pro",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )

    # Relationships INTENTIONALLY OMITTED in iam-svc.
    # The cross-schema FKs to users.id were dropped by migration b1c2d3e4f5a6.
    # iam-svc only needs User for identity lookup — no traversal to sibling tables.
    # (Compare monolith app/shared/models/user.py which has 6 relationships.)
