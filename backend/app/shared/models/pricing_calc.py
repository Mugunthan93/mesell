"""Pricing calculation ORM model.

Table: ``pricing_calcs``
DDL source: V1_FEATURE_SPEC §4 lines 472-484 (authoritative per coordinator contract)

Scopes to a product via ``product_id`` FK.  No ``user_id`` on this table —
tenant isolation is enforced through the product → catalog → user FK chain.
Service layer always resolves via product (which carries user_id) before
querying pricing_calcs.

NUMERIC types: (10,2) for monetary fields, (5,2) for percentages.

Column history
--------------
baseline (935e55b4852c): id, product_id, mrp, meesho_price, seller_price,
    commission_pct, gst_pct, margin, margin_pct, created_at

b7c2e1a9d3f4 (#285 forward-estimator, now superseded):
    estimated_payout, referral_commission, shipping_charge, logistics_fee,
    fixed_fee, gst_on_fees, tcs, tds, rto_expected_loss, return_rate_pct,
    markup_pct, wdrp_price

W2 confirmed-model (this migration, down_rev c2d3e4f5a6b7):
    selling_price, shipping, total_price, commission_fees, gst_on_shipping,
    estimated_bank_settlement, meesho_leaf_id
    NOTE: tcs + tds were already added by b7c2e1a9d3f4; the confirmed model
    adopts them with corrected semantics — no DDL change to those two columns.
    commission_pct was in the baseline; confirmed model re-uses it unchanged.

#285 wrong-model columns are retained nullable per Q3 KEEP-NULLABLE ruling
(dev-only; not on staging/prod; never written by W2+ service layer).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base

if TYPE_CHECKING:
    from app.shared.models.product import Product


class PricingCalc(Base):
    __tablename__ = "pricing_calcs"

    # ── Primary key + tenant anchor ────────────────────────────────────────────
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

    # ── CONFIRMED MODEL (W2) — census-verified settlement breakdown ────────────
    # Math source: project_pricing_transfer_price_model.md (2026-06-19).
    # The W2+ service layer writes ONLY these columns (+ commission_pct reused).
    # tcs + tds columns exist from migration b7c2e1a9d3f4 and are adopted here
    # with corrected semantics; no DDL change to those two columns.
    selling_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="Seller's listed Meesho price — request echo (confirmed model W2)",
    )
    shipping: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="Per-category flat shipping constant from pricing lookup (confirmed model W2)",
    )
    total_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="selling_price + shipping (confirmed model W2)",
    )
    commission_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        comment=(
            "Commission % actually applied — 0 default (confirmed model W2). "
            "Column exists since baseline; semantics unchanged."
        ),
    )
    commission_fees: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="commission_pct x selling_price (confirmed model W2)",
    )
    gst_on_shipping: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="18% x shipping — the seller's actual shipping cost (confirmed model W2)",
    )
    tds: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment=(
            "0.1% x total_price — TDS deduction (confirmed model W2). "
            "Column added by b7c2e1a9d3f4; adopted here with correct semantics."
        ),
    )
    tcs: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment=(
            "Tax collected at source — always 0 per census (confirmed model W2). "
            "Column added by b7c2e1a9d3f4; adopted here with correct semantics."
        ),
    )
    estimated_bank_settlement: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment=(
            "selling_price - commission_fees - gst_on_shipping - tds - tcs "
            "(confirmed model W2 headline output)"
        ),
    )
    meesho_leaf_id: Mapped[str | None] = mapped_column(
        String(16),
        comment="Meesho sscat_id used for the per-category shipping lookup (confirmed model W2)",
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # ── DEPRECATED #285 wrong-model columns ────────────────────────────────────
    # Added by merged PR #285 (forward-estimator, now superseded by confirmed model).
    # KEEP NULLABLE per Q3 RESOLVED ruling: dev-only; not on staging/prod.
    # W2+ service layer NEVER writes to these columns.
    # Scheduled for two-step drop in a future V1.5 cleanup migration.
    mrp: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="DEPRECATED #285 wrong-model column — kept nullable per Q3, never written by W2+",
    )
    meesho_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="DEPRECATED #285 wrong-model column — kept nullable per Q3, never written by W2+",
    )
    seller_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="DEPRECATED #285 wrong-model column — kept nullable per Q3, never written by W2+",
    )
    gst_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        comment="DEPRECATED #285 wrong-model column — kept nullable per Q3, never written by W2+",
    )
    margin: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="DEPRECATED #285 wrong-model column — kept nullable per Q3, never written by W2+",
    )
    margin_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        comment="DEPRECATED #285 wrong-model column — kept nullable per Q3, never written by W2+",
    )
    estimated_payout: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="DEPRECATED #285 wrong-model column — kept nullable per Q3, never written by W2+",
    )
    referral_commission: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="DEPRECATED #285 wrong-model column — kept nullable per Q3, never written by W2+",
    )
    shipping_charge: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="DEPRECATED #285 wrong-model column — kept nullable per Q3, never written by W2+",
    )
    logistics_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="DEPRECATED #285 wrong-model column — kept nullable per Q3, never written by W2+",
    )
    fixed_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="DEPRECATED #285 wrong-model column — kept nullable per Q3, never written by W2+",
    )
    gst_on_fees: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="DEPRECATED #285 wrong-model column — kept nullable per Q3, never written by W2+",
    )
    rto_expected_loss: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="DEPRECATED #285 wrong-model column — kept nullable per Q3, never written by W2+",
    )
    return_rate_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        comment="DEPRECATED #285 wrong-model column — kept nullable per Q3, never written by W2+",
    )
    markup_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        comment="DEPRECATED #285 wrong-model column — kept nullable per Q3, never written by W2+",
    )
    wdrp_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        comment="DEPRECATED #285 wrong-model column — kept nullable per Q3, never written by W2+",
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
