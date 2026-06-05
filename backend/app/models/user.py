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

from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.seller_profile import SellerProfile
    from app.models.catalog import Catalog
    from app.models.product import Product
    from app.models.export import Export
    from app.models.audit_event import AuditEvent
    from app.models.product_draft import ProductDraft


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    phone: Mapped[str] = mapped_column(
        String(15),
        unique=True,
        nullable=False,
        index=True,
        comment="E.164 format Indian mobile, e.g. +919876543210",
    )
    email: Mapped[str | None] = mapped_column(String(255))
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
        back_populates="user",
    )
    product_drafts: Mapped[list[ProductDraft]] = relationship(
        "ProductDraft",
        back_populates="user",
        cascade="all, delete-orphan",
    )
