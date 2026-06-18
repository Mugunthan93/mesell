"""``pricing`` internal domain types — frozen dataclasses.

Per BACKEND_ARCHITECTURE.md §12.F (LOCKED 2026-06-05) as superseded by the
**§12.M AMENDMENT 2026-06-18 — Price Calculator forward-estimator rework**.

The objects defined here are NOT Pydantic models — they never cross the
HTTP boundary.  The service serialises them to Pydantic wire-shape models
(:class:`~app.modules.pricing.schemas.PriceCalcResponse` /
:class:`~app.modules.pricing.schemas.PriceCalcAlert`) via straight
field-mapping.

Locked alert rules (§12.M (3))
------------------------------
* ``NEGATIVE_PAYOUT``    — ``estimated_payout < 0``                    — severity ``warning``
* ``LOW_MARGIN``         — ``margin_pct < 10``                        — severity ``warning``
* ``SHIPPING_DOMINATES`` — ``shipping > 40% of total_deductions``     — severity ``info``

Multiple alerts may fire simultaneously.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID


# ─────────────────────────────────────────────────────────────────────────────
# PricingCalc — mirrors a pricing_calcs row.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class PricingCalc:
    """Mirrors a ``pricing_calcs`` row — returned by repository methods.

    Per §12.M (5) the table gained additive nullable breakdown columns and
    re-purposed ``commission_pct`` as the seller-entered commission
    snapshot.  Tenant isolation is enforced through the product → catalog →
    user FK chain; the service layer always asserts
    ``catalog.assert_product_ownership(product_id, user_id)`` BEFORE any
    ``pricing_calcs`` read or write.
    """

    id: UUID
    product_id: UUID
    mrp: Decimal | None
    meesho_price: Decimal
    # Legacy ``seller_price`` column re-used as the estimated payout snapshot.
    seller_price: Decimal
    commission_pct: Decimal
    gst_pct: Decimal
    margin: Decimal
    """Absolute profit (estimated_payout − input_cost) — DDL column ``margin``."""
    margin_pct: Decimal
    """Margin percentage (profit / meesho_price × 100) — DDL column ``margin_pct``."""
    # §12.M (5) additive nullable breakdown columns.
    estimated_payout: Decimal | None
    referral_commission: Decimal | None
    shipping_charge: Decimal | None
    logistics_fee: Decimal | None
    fixed_fee: Decimal | None
    gst_on_fees: Decimal | None
    tcs: Decimal | None
    tds: Decimal | None
    rto_expected_loss: Decimal | None
    return_rate_pct: Decimal | None
    markup_pct: Decimal | None
    wdrp_price: Decimal | None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# PnLBreakdown — internal output of _estimate_payout.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class PnLBreakdown:
    """Internal — output of the deterministic forward estimator
    :func:`_estimate_payout`.

    Not Pydantic; never crosses HTTP.  Consumed by
    :func:`_generate_alerts` and serialized into ``PriceCalcResponse`` at
    the route boundary.

    All monetary values are :class:`~decimal.Decimal` with 2 dp
    quantization (``ROUND_HALF_EVEN``) — never :class:`float`.
    """

    meesho_price: Decimal
    input_cost: Decimal
    commission_pct: Decimal
    referral_commission: Decimal
    shipping_charge: Decimal
    logistics_fee: Decimal
    fixed_fee: Decimal
    gst_pct: Decimal
    gst_on_fees: Decimal
    tcs: Decimal
    tds: Decimal
    return_rate_pct: Decimal
    rto_expected_loss: Decimal
    total_deductions: Decimal
    estimated_payout: Decimal
    profit: Decimal
    margin_pct: Decimal
    markup_pct: Decimal


# ─────────────────────────────────────────────────────────────────────────────
# PricingAlert
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class PricingAlert:
    """Internal alert dataclass.

    Lives in ``modules/pricing/domain.py`` per the §3.C per-module
    canonical 7-file subtree.  The service maps each ``PricingAlert`` to a
    wire-shape ``PriceCalcAlert`` in ``schemas.py`` via straight field copy
    (``code`` / ``message_id`` / ``severity``).
    """

    code: Literal["NEGATIVE_PAYOUT", "LOW_MARGIN", "SHIPPING_DOMINATES"]
    message_id: str
    """``validation_message_id`` per §5A.H — e.g. ``pricing.alert.negative_payout``."""
    severity: Literal["warning", "info"]


__all__ = [
    "PricingCalc",
    "PnLBreakdown",
    "PricingAlert",
]
