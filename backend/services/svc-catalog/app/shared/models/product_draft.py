"""Product draft ORM model — vendored for svc-catalog, bound to ``catalog``.

Table: ``catalog.product_drafts``
DDL source: MVP_ARCHITECTURE §10 / §11.6

The ``product_drafts`` table moved ``public`` → ``catalog`` in MS-H Phase A
(migration ``a8f3b2e9c1d5``).  Bound to ``{"schema": "catalog"}``.

Design:
  - Composite PK (user_id, product_id) — one row per product per user.
  - ``draft_jsonb`` stores the FULL current field state (wrapped envelope
    ``{"fields": ..., "autosave_count": int}`` per §10-CATALOG-D1).
  - On successful export, the row is deleted.
  - GET /api/v1/products/{id}/draft returns it to re-hydrate the wizard.

Cross-schema FK handling (SUB_PLAN_0H §DB / R6)
----------------------------------------------
* INTRA-schema (both sides in ``catalog`` — KEPT): ``product_id →
  catalog.products.id`` FK constraint + the ``product`` relationship.
* CROSS-schema (DROPPED as SQLAlchemy FK/relationship — DB FK preserved):
  ``user_id → public.users.id`` (→ iam.users).  Bare UUID PK column; the
  ``user`` relationship is dropped (the ``User`` ORM is iam-owned, not
  vendored as a related model here — only the public-bound existence-check
  mirror is vendored for ``core/auth``).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKeyConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base

if TYPE_CHECKING:
    from app.shared.models.product import Product


class ProductDraft(Base):
    __tablename__ = "product_drafts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment="Tenant owner (part of composite PK)",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment="Product this draft belongs to (part of composite PK)",
    )
    # Full wizard field state — not a diff.
    draft_jsonb: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Full wizard field state for crash recovery — upserted on every PATCH",
    )
    saved_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        comment="Timestamp of last upsert",
    )

    # Relationships — INTRA-schema only.  The cross-schema ``user``
    # relationship is DROPPED (§2.D).
    product: Mapped[Product] = relationship(
        "Product",
        back_populates="draft",
        foreign_keys=[product_id],
    )

    # Table-level DDL — INTRA-schema FK to catalog.products KEPT (schema-
    # qualified); the cross-schema FK to public.users is preserved at the DB
    # level but NOT declared as a SQLAlchemy constraint here (§2.D).  Indexes
    # on product_id + saved_at preserved.  Bound to the ``catalog`` schema.
    __table_args__ = (
        ForeignKeyConstraint(
            ["product_id"],
            ["catalog.products.id"],
            ondelete="CASCADE",
            name="fk_product_drafts_product_id",
        ),
        Index("idx_product_drafts_product_id", "product_id"),
        # G10 — staleness driver index for TTL cleanup task.
        Index("idx_product_drafts_saved_at", "saved_at"),
        {"schema": "catalog"},
    )
