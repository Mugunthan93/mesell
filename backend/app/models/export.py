"""Export ORM model — Meesho XLSX export record.

Table: ``exports``
DDL source: V1_FEATURE_SPEC §4 lines 486-496 (authoritative per coordinator contract)

``user_id`` FK is explicit on this table (per V1_FEATURE_SPEC DDL) to allow
direct tenant-scoped queries without joining through products.
``product_id`` FK is RESTRICT (not CASCADE) — exports are records of a past
action and should not auto-delete if a product is soft-deleted.

``status`` lifecycle: processing → ready | failed
``error_message`` is a V1 addition (not in V1_FEATURE_SPEC DDL) — needed to
surface failures from the Celery export task (§5.5.8) to the polling endpoint.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.user import User


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Tenant owner — explicit FK for direct tenant-scoped queries",
    )
    xlsx_gcs_path: Mapped[str | None] = mapped_column(
        Text,
        comment="GCS object path for the generated XLSX file",
    )
    zip_gcs_path: Mapped[str | None] = mapped_column(
        Text,
        comment="GCS object path for the images ZIP file",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'processing'"),
        comment="processing | ready | failed",
    )
    download_url: Mapped[str | None] = mapped_column(
        Text,
        comment="Signed GCS URL for download (TTL 1h) — set once status=ready",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        comment="Set when status=failed; may be seller-facing or internal",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    product: Mapped[Product] = relationship(
        "Product",
        back_populates="exports",
    )
    user: Mapped[User] = relationship(
        "User",
        back_populates="exports",
        foreign_keys=[user_id],
    )

    # Indexes — both FKs indexed for tenant-scoped queries
    __table_args__ = (
        Index("idx_exports_product_id", "product_id"),
        Index("idx_exports_user_id", "user_id"),
    )
