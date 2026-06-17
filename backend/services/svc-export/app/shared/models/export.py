"""Export ORM model — vendored for svc-export, bound to schema ``export``.

Mirrors the monolith ``app.shared.models.export.Export`` column shape
(V1_FEATURE_SPEC §4 DDL) but:

1. binds to the ``export`` Postgres schema via
   ``__table_args__ = {"schema": "export"}`` (Sub-Plan A schema-split —
   the table was moved ``public.exports`` → ``export.exports`` by the
   svc-export Alembic migration ``e7a3c1f9b42d``);
2. DROPS the cross-schema ORM relationships to ``Product`` and ``User``
   (the export repository queries scalar columns + tenant-scopes on
   ``user_id`` only — it never traverses a relationship, and the FK is a
   schema-isolation concern handled at the DB layer, not the ORM).

Column shape is byte-identical to the monolith model so the repository
``_orm_to_domain`` derivations (§14-EXPORT-D1..D6) behave identically.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Index, String, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base


class Export(Base):
    __tablename__ = "exports"
    # Sub-Plan A schema-split: the table lives in the ``export`` schema.
    __table_args__ = (
        Index("idx_exports_product_id", "product_id"),
        Index("idx_exports_user_id", "user_id"),
        {"schema": "export"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    # FK references dropped at the ORM layer (schema isolation) — plain UUIDs.
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Tenant owner — explicit column for direct tenant-scoped queries",
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
        comment="Signed GCS URL for download (TTL 1h) — vestigial per §14-EXPORT-D6",
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
