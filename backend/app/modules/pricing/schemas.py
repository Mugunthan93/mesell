"""``pricing`` Pydantic v2 wire-shape models — request + response surfaces.

Per BACKEND_ARCHITECTURE.md §12.E (LOCKED 2026-06-05) as superseded by the
**§12.M AMENDMENT 2026-06-18 — Price Calculator forward-estimator rework
(founder-ratified)**.

Forward estimator (§12.M)
-------------------------
The calculator runs FORWARD: the seller enters a **Meesho Price** (the
listed price) and the backend estimates the **net payout**.  Profit and
margin are *outputs*, never inputs.  ``target_margin_pct`` is REMOVED.

* :class:`PriceCalcRequest` — ``meesho_price`` is the primary input;
  ``commission_pct`` is a **seller input** (default 4%), NOT a category
  lookup; the full deduction stack is computed deterministically.
* :class:`PriceCalcResponse` — the 3-price model (MRP reference, Meesho
  Price, WDRP) + the full deduction breakdown + ``estimated_payout`` +
  ``estimated_payout_wdrp`` + ``profit`` + ``margin_pct`` + ``markup_pct``
  + alerts + ``calculated_at``.

All monetary values are :class:`~decimal.Decimal` with 2 dp — never
:class:`float` per CLAUDE.md "Coding Conventions" + §4.D numeric
precision rule.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# Request (§12.M (2))
# ─────────────────────────────────────────────────────────────────────────────
class PriceCalcRequest(BaseModel):
    """Body for ``POST /api/v1/products/{id}/price-calc``.

    Per §12.M.  Pydantic validates the field constraints at the route
    boundary; service-layer business-rule checks are surfaced via
    :class:`~app.modules.pricing.exceptions.InvalidPriceInputError` (400).
    A negative estimated payout does NOT raise — it returns 200 with a
    ``NEGATIVE_PAYOUT`` alert.
    """

    model_config = ConfigDict(extra="forbid")

    # ── Primary inputs ───────────────────────────────────────────────────
    meesho_price: Decimal = Field(
        gt=0,
        decimal_places=2,
        description="Listed/selling price on Meesho, in INR — drives the payout.",
    )
    input_cost: Decimal = Field(
        gt=0,
        decimal_places=2,
        description="Cost of goods per unit, in INR — drives profit + markup.",
    )

    # ── Seller-entered estimator inputs ──────────────────────────────────
    commission_pct: Decimal = Field(
        default=Decimal("4"),
        ge=0,
        le=Decimal("100"),
        decimal_places=2,
        description="Meesho referral commission %, seller-entered (default 4%).",
    )
    return_rate_pct: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        le=Decimal("100"),
        decimal_places=2,
        description="Expected return rate %, drives the RTO expected-loss term.",
    )

    # ── Optional display reference ───────────────────────────────────────
    mrp: Decimal | None = Field(
        default=None,
        gt=0,
        decimal_places=2,
        description="Struck-through reference price (display-only; does NOT drive payout).",
    )

    # ── Tunable per-request deduction overrides ──────────────────────────
    override_shipping: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Override the bracketed shipping charge (INR).",
    )
    override_logistics_fee: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Override the logistics fee (INR).",
    )
    override_fixed_fee: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Override the fixed/closing fee (INR).",
    )
    override_gst_pct: Decimal | None = Field(
        default=None,
        ge=0,
        le=Decimal("100"),
        decimal_places=2,
        description="Override the GST % applied to the fees.",
    )
    override_tcs_pct: Decimal | None = Field(
        default=None,
        ge=0,
        le=Decimal("100"),
        decimal_places=2,
        description="Override the TCS %.",
    )
    override_tds_pct: Decimal | None = Field(
        default=None,
        ge=0,
        le=Decimal("100"),
        decimal_places=2,
        description="Override the TDS %.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Alert (wire shape) (§12.M (3))
# ─────────────────────────────────────────────────────────────────────────────
class PriceCalcAlert(BaseModel):
    """Wire-shape pricing alert.  See
    :class:`~app.modules.pricing.domain.PricingAlert` for the internal
    dataclass that the service constructs and the router maps to this
    Pydantic model."""

    code: Literal["NEGATIVE_PAYOUT", "LOW_MARGIN", "SHIPPING_DOMINATES"]
    message_id: str = Field(
        description="validation_message_id per §5A.H — resolved client-side via i18n.",
    )
    severity: Literal["warning", "info"]


# ─────────────────────────────────────────────────────────────────────────────
# Response (§12.M)
# ─────────────────────────────────────────────────────────────────────────────
class PriceCalcResponse(BaseModel):
    """200-OK body for ``POST /api/v1/products/{id}/price-calc``.

    All monetary values in INR with 2 decimal places (quantized
    ``ROUND_HALF_EVEN`` per the §12.M lock).
    """

    # ── 3-price model ────────────────────────────────────────────────────
    mrp: Decimal | None
    """Struck-through reference price (echoed from the request; may be None)."""
    meesho_price: Decimal
    wdrp_price: Decimal
    """Wrong/Defective Return Price = meesho_price − WDRP_DELTA."""

    # ── Seller cost (echo) ───────────────────────────────────────────────
    input_cost: Decimal

    # ── Deduction breakdown ──────────────────────────────────────────────
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

    # ── Outputs ──────────────────────────────────────────────────────────
    estimated_payout: Decimal
    estimated_payout_wdrp: Decimal
    profit: Decimal
    margin_pct: Decimal
    markup_pct: Decimal

    alerts: list[PriceCalcAlert]
    calculated_at: datetime


__all__ = [
    "PriceCalcRequest",
    "PriceCalcAlert",
    "PriceCalcResponse",
]
