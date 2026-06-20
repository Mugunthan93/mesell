"""User identity ORM model.

Table: ``users``
DDL source: MVP_ARCHITECTURE §2.1

PKs are UUID via ``gen_random_uuid()`` (requires pgcrypto extension — enabled in
Phase 2 baseline migration).  All timestamps are TIMESTAMPTZ (timezone-aware).

Relationships use string-based forward references; all models are loaded by
``app.models.__init__`` in dependency order before any query is executed.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base

if TYPE_CHECKING:
    from app.shared.models.seller_profile import SellerProfile
    from app.shared.models.catalog import Catalog
    from app.shared.models.product import Product
    from app.shared.models.export import Export
    from app.shared.models.audit_event import AuditEvent
    from app.shared.models.product_draft import ProductDraft


class User(Base):
    __tablename__ = "users"
    # google-auth (2026-06-18): table-level CHECK guarantees every row carries
    # at least one authentication identity (phone OR google_sub).  Migration
    # c2d3e4f5a6b7 adds the constraint; it validates immediately on existing
    # rows (all have a phone).
    __table_args__ = (
        CheckConstraint(
            "phone IS NOT NULL OR google_sub IS NOT NULL",
            name="ck_users_at_least_one_identity",
        ),
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

    # Relationships — string references resolved at mapper-configuration time
    seller_profile: Mapped[SellerProfile | None] = relationship(
        "SellerProfile",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    catalogs: Mapped[list[Catalog]] = relationship(
        "Catalog",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    products: Mapped[list[Product]] = relationship(
        "Product",
        back_populates="user",
        foreign_keys="[Product.user_id]",
    )
    exports: Mapped[list[Export]] = relationship(
        "Export",
        back_populates="user",
        foreign_keys="[Export.user_id]",
        cascade="all, delete-orphan",
    )
    audit_events: Mapped[list[AuditEvent]] = relationship(
        "AuditEvent",
        viewonly=True,
    )
    product_drafts: Mapped[list[ProductDraft]] = relationship(
        "ProductDraft",
        back_populates="user",
        cascade="all, delete-orphan",
    )
