"""Pricing calculation ORM model — vendored for svc-pricing, bound to ``pricing``.

Table: ``pricing.pricing_calcs``
DDL source: V1_FEATURE_SPEC §4 lines 472-484 (authoritative per coordinator contract)

The ``pricing_calcs`` table moved ``public`` → ``pricing`` in MS-D Phase A
(migration ``97c9dd63f587`` — ``ALTER TABLE pricing_calcs SET SCHEMA pricing``).
This vendored model binds ``{"schema": "pricing"}`` explicitly so every
``pricing_calcs`` read/write lands in the owned schema.

Cross-schema FK (§0.6 / spec §3.C)
----------------------------------
The DB-level FK ``pricing_calcs.product_id → public.products.id`` is KEPT VALID
in the database (PostgreSQL cross-schema FKs are legal; it is dropped only at
catalog extraction MS-H, NOT here).  But this vendored ORM model does NOT
declare a SQLAlchemy ``ForeignKey`` or ``relationship`` to ``Product`` because
the ``Product`` ORM model is CATALOG-owned and is NOT vendored into svc-pricing
(per §2.D no cross-schema ORM).  ``product_id`` is therefore a bare ``UUID``
column here — the FK integrity is enforced by the database constraint, not the
ORM mapper.  This is the §0.6 ``ProductORM`` elimination at the model layer.

Scopes to a product via ``product_id``.  No ``user_id`` on this table —
tenant isolation is enforced through the product → user ownership chain,
asserted UPSTREAM at the catalog ``assert_product_ownership`` HTTP shim
(§0.6 Option B) BEFORE any pricing_calcs read or write.

NUMERIC types: (10,2) for monetary fields, (5,2) for percentages —
matches the V1_FEATURE_SPEC DDL exactly.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Index, Numeric, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base


class PricingCalc(Base):
    __tablename__ = "pricing_calcs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        # NO SQLAlchemy ForeignKey here — ``products`` is catalog-owned and not
        # vendored (§0.6).  The DB-level cross-schema FK to public.products
        # remains in force; the ORM treats this as a bare UUID column.
    )
    mrp: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="Maximum Retail Price entered by seller",
    )
    meesho_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="Listing price on Meesho (seller-facing price)",
    )
    seller_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="Amount Meesho remits to seller after commission deduction",
    )
    commission_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        comment="Meesho commission rate for the product's category",
    )
    gst_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        comment="GST rate applicable to the product",
    )
    margin: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="Absolute margin (seller_price - cost of goods) in INR",
    )
    margin_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        comment="Margin as percentage of seller_price",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Index the FK column + bind the owned ``pricing`` schema (§0.6 / MS-D Phase A).
    __table_args__ = (
        Index("idx_pricing_calcs_product_id", "product_id"),
        {"schema": "pricing"},
    )
