"""CategorySnapshot ORM model — diff source-of-truth for category change monitor.

Table: ``category_snapshots``
DDL source: RETENTION_CATEGORY_MONITOR.md §2.2

Stores one row per (category_id, capture event).  The ``content_hash`` is the
cheap change-detector: if the new scrape's hash equals the latest row's hash,
the diff/fan-out path short-circuits with no notification.

The raw blob lives in GCS at ``data/snapshots/<YYYY-MM-DD>/cat_<category_id>.json``;
``blob_uri`` is a nullable pointer to that object (NULL while the GCS write is
in-flight, or for locally-scraped test runs).

Index strategy:
    ``idx_category_snapshot_latest`` on ``(category_id, captured_at DESC)`` is
    the load-bearing index for "latest snapshot for category" queries — a
    covering-prefix composite that also covers category_id-only lookups.
    No separate single-column ``category_id`` index is added (leftmost-prefix
    covers it per B-tree semantics).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base

if TYPE_CHECKING:
    from app.shared.models.category import Category


class CategorySnapshot(Base):
    __tablename__ = "category_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        comment="Category this snapshot captures",
    )
    captured_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        comment="Timestamp when the scrape ran",
    )
    # SHA-256 (or equivalent 64-hex) of the captured rule surface.
    # Equality against the previous row's hash is the cheap change-detector.
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Hex content hash — equality check short-circuits diff/fan-out",
    )
    # Structured projection of the captured rule surface for diffing.
    # Shape: {compliance_fields, shipping_slab, banned_words, cost_fields}
    dimensions_jsonb: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="Captured category rule dimensions for diff engine input",
    )
    # Nullable pointer to the raw GCS blob (NULL while in-flight or in tests).
    blob_uri: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="GCS object URI for the raw snapshot blob, NULL until upload completes",
    )

    # Relationships
    category: Mapped[Category] = relationship(
        "Category",
        foreign_keys=[category_id],
    )

    __table_args__ = (
        # Primary query pattern: latest snapshot for a given category.
        # Composite leftmost-prefix also covers category_id-only seeks.
        Index(
            "idx_category_snapshot_latest",
            "category_id",
            "captured_at",
            postgresql_using="btree",
        ),
    )
