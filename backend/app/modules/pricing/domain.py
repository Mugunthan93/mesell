"""``pricing`` internal domain types — frozen dataclasses.

Per BACKEND_ARCHITECTURE.md §12.C/§12.F (LOCKED 2026-06-05) as superseded by
the **W2 Price Calculator rework (census-confirmed settlement model,
2026-06-19)** — see
``.claude/agent-memory/nexus-level-0-director/project_pricing_transfer_price_model.md``.

The objects defined here are NOT Pydantic models — they never cross the
HTTP boundary.  The service serialises them to Pydantic wire-shape models
(:class:`~app.modules.pricing.schemas.PriceCalcResponse` /
:class:`~app.modules.pricing.schemas.PriceCalcAlert`) via straight
field-mapping.

The confirmed settlement formula (verified on 3,772/3,772 categories +
the founder's first real order — SKU TTC-BL-OR-HP-NG-P4 → ₹61.78)::

    shipping        = pricing_lookup.get_shipping(meesho_leaf_id)  # per-category constant
    commission_pct  = request override else 0
    commission_fees = commission_pct × selling_price
    total_price     = selling_price + shipping
    gst_on_shipping = 0.18 × shipping
    tds             = 0.001 × total_price
    tcs             = 0
    estimated_bank_settlement
                    = selling_price − commission_fees − gst_on_shipping − tds − tcs

The seller-side true-profit layer is DEFERRED to V1.5 — this module ships
only the Meesho bank-settlement estimate, not seller profitability.

Locked alert rule (V1 ships ONE)
--------------------------------
* ``NEGATIVE_SETTLEMENT`` — ``estimated_bank_settlement < 0`` — severity ``warning``
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID


# ─────────────────────────────────────────────────────────────────────────────
# PricingCalc — mirrors a pricing_calcs row (confirmed-model column set).
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class PricingCalc:
    """Mirrors a ``pricing_calcs`` row — returned by repository methods.

    Only the confirmed-model columns (W2) are represented here; the
    deprecated #285 columns are kept nullable in the DDL but are never
    written and are not part of this domain shape.  Tenant isolation is
    enforced through the product → catalog → user FK chain; the service
    layer always asserts ``catalog.assert_product_ownership(product_id,
    user_id)`` BEFORE any ``pricing_calcs`` read or write.
    """

    id: UUID
    product_id: UUID
    selling_price: Decimal
    shipping: Decimal
    total_price: Decimal
    commission_pct: Decimal
    commission_fees: Decimal
    gst_on_shipping: Decimal
    tds: Decimal
    tcs: Decimal
    estimated_bank_settlement: Decimal
    meesho_leaf_id: str
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# SettlementBreakdown — internal output of _compute_settlement.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class SettlementBreakdown:
    """Internal — output of the deterministic settlement calculator
    :func:`~app.modules.pricing.service._compute_settlement`.

    Not Pydantic; never crosses HTTP.  Consumed by ``_generate_alerts`` and
    serialized into ``PriceCalcResponse`` at the route boundary.

    All monetary values are :class:`~decimal.Decimal` quantized to 2 dp via
    ``ROUND_HALF_UP`` — never :class:`float`.
    """

    selling_price: Decimal
    shipping: Decimal
    total_price: Decimal
    commission_pct: Decimal
    commission_fees: Decimal
    gst_on_shipping: Decimal
    tds: Decimal
    tcs: Decimal
    estimated_bank_settlement: Decimal


# ─────────────────────────────────────────────────────────────────────────────
# PricingAlert — V1 ships exactly one alert code.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class PricingAlert:
    """Internal alert dataclass.

    Lives in ``modules/pricing/domain.py`` per the §3.C per-module
    canonical 7-file subtree.  The service maps each ``PricingAlert`` to a
    wire-shape ``PriceCalcAlert`` in ``schemas.py`` via straight field copy
    (``code`` / ``message_id`` / ``severity``).
    """

    code: Literal["NEGATIVE_SETTLEMENT"]
    message_id: str
    """``validation_message_id`` per §5A.H — ``pricing.alert.negative_settlement``."""
    severity: Literal["warning"]


__all__ = [
    "PricingCalc",
    "SettlementBreakdown",
    "PricingAlert",
]
