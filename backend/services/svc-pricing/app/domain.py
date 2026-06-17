"""``pricing`` internal domain types — frozen dataclasses.

Per BACKEND_ARCHITECTURE.md §12.F (LOCKED 2026-06-05).  Vendored byte-for-byte
into svc-pricing (spec §3.A) — self-contained, no cross-module imports.

This file is the NEW home of :class:`PricingAlert` — the §0.E latent bug
resolution.  The legacy ``backend/app/schemas/pricing.py`` was deleted in the
§G3 gap pass; the legacy ``backend/app/services/pricing_engine.py`` was deleted
at §12 construction time per §12.A.  The new :class:`PricingAlert` here replaces
both — and is the single canonical home of the alert dataclass per §3.C
``modules/<X>/domain.py``.

The objects defined here are NOT Pydantic models — they never cross the HTTP
boundary.  The router serialises them to Pydantic wire-shape models
(``PriceCalcResponse`` / ``PriceCalcAlert`` in ``schemas.py``) via straight
field-mapping.

Locked alert rules (§12.F + §12.J test #4)
------------------------------------------
* ``LOW_MARGIN``         — ``profit_pct < 10``                — severity ``warning``
* ``HIGH_MRP_MULTIPLIER``— ``mrp / input_cost > 3``           — severity ``warning``
* ``THIN_PROFIT``        — ``profit < 50`` (INR)              — severity ``info``

Multiple alerts may fire simultaneously (e.g. low ``input_cost`` + low
``target_margin_pct`` → both ``THIN_PROFIT`` and ``LOW_MARGIN``).
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

    DECISION FLAG §12-PRICING-D4 — DDL is the law
    --------------------------------------------
    The actual ``pricing_calcs`` DDL (Wave 1 LOCKED) carries structured
    monetary columns (``mrp / meesho_price / seller_price /
    commission_pct / gst_pct / margin / margin_pct / created_at``) — NOT
    the ``{user_id, input_jsonb, output_jsonb, calculated_at}`` shape
    quoted in §12.B.1 step 8 prose.  We honor the DDL.

    Tenant isolation is enforced through the product → catalog → user FK
    chain per the ORM model docstring; the service layer always asserts
    ``catalog.assert_product_ownership(product_id, user_id)`` BEFORE any
    pricing_calcs read or write.
    """

    id: UUID
    product_id: UUID
    mrp: Decimal
    meesho_price: Decimal
    seller_price: Decimal
    commission_pct: Decimal
    gst_pct: Decimal
    margin: Decimal
    """Absolute profit (seller_price − input_cost) — DDL column name
    ``margin`` per the §5.E ORM registry."""
    margin_pct: Decimal
    """Profit percentage (margin / input_cost × 100) — DDL column name
    ``margin_pct`` per the §5.E ORM registry."""
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# PnLBreakdown — internal output of _compute_pnl.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class PnLBreakdown:
    """Internal — output of the deterministic :func:`_compute_pnl` function.

    Not Pydantic; never crosses HTTP.  Consumed by
    :func:`_generate_alerts` and serialized into ``PriceCalcResponse`` at
    the route boundary.

    All monetary values are :class:`~decimal.Decimal` with 2 dp
    quantization (``ROUND_HALF_EVEN``) — never :class:`float`.
    """

    mrp: Decimal
    meesho_price: Decimal
    seller_price: Decimal
    commission_pct: Decimal
    commission_amount: Decimal
    gst_pct: Decimal
    gst_amount: Decimal
    profit: Decimal
    profit_pct: Decimal


# ─────────────────────────────────────────────────────────────────────────────
# PricingAlert — REPLACES the deleted legacy schemas/pricing.PricingAlert.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class PricingAlert:
    """Internal alert dataclass — REPLACES the legacy
    ``backend/app/schemas/pricing.PricingAlert`` (deleted in session 2 gap
    pass; §0.E latent bug resolution per §12.A).

    Lives in ``modules/pricing/domain.py`` per the §3.C per-module
    canonical 7-file subtree.

    The router maps each ``PricingAlert`` to a wire-shape
    ``PriceCalcAlert`` in ``schemas.py`` via straight field copy
    (``code`` / ``message_id`` / ``severity``).
    """

    code: Literal["LOW_MARGIN", "HIGH_MRP_MULTIPLIER", "THIN_PROFIT"]
    message_id: str
    """``validation_message_id`` per §5A.H — e.g. ``pricing.alert.low_margin``."""
    severity: Literal["warning", "info"]


__all__ = [
    "PricingCalc",
    "PnLBreakdown",
    "PricingAlert",
]
