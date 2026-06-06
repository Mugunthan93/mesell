"""Pricing calculation ORM model.

Table: ``pricing_calcs``
DDL source: V1_FEATURE_SPEC §4 lines 472-484 (authoritative per coordinator contract)

Scopes to a product via ``product_id`` FK.  No ``user_id`` on this table —
tenant isolation is enforced through the product → catalog → user FK chain.
Service layer always resolves via product (which carries user_id) before
querying pricing_calcs.

NUMERIC types: (10,2) for monetary fields, (5,2) for percentages —
matches the V1_FEATURE_SPEC DDL exactly.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Numeric, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base

if TYPE_CHECKING:
    from app.shared.models.product import Product


class PricingCalc(Base):
    __tablename__ = "pricing_calcs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
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

    # Relationship
    product: Mapped[Product] = relationship(
        "Product",
        back_populates="pricing_calcs",
    )

    # Index the FK
    __table_args__ = (
        Index("idx_pricing_calcs_product_id", "product_id"),
    )
