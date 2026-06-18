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
        comment="Seller-entered referral commission % snapshot (§12.M)",
    )
    gst_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        comment="GST rate applied to the fees",
    )
    margin: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="Absolute profit (estimated_payout - cost of goods) in INR",
    )
    margin_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        comment="Margin as percentage of meesho_price",
    )
    # ── §12.M (5) additive nullable forward-estimator breakdown columns ──
    estimated_payout: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="Net payout estimate = meesho_price - total_deductions",
    )
    referral_commission: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="meesho_price x commission_pct / 100",
    )
    shipping_charge: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="Bracketed flat shipping charge (INR)",
    )
    logistics_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="Logistics fee (INR)",
    )
    fixed_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="Fixed/closing fee (INR)",
    )
    gst_on_fees: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="GST on the fee base (not on MRP)",
    )
    tcs: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="Tax collected at source on meesho_price",
    )
    tds: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="Tax deducted at source on meesho_price",
    )
    rto_expected_loss: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="return_rate_pct x (shipping + logistics)",
    )
    return_rate_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        comment="Seller-entered expected return rate %",
    )
    markup_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        comment="Markup as percentage of input_cost (profit / input_cost)",
    )
    wdrp_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="Wrong/Defective Return Price = meesho_price - WDRP_DELTA",
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
