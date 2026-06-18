"""``pricing`` service layer — forward payout estimator + cross-module
orchestration.

Per BACKEND_ARCHITECTURE.md §12.C (LOCKED 2026-06-05) as superseded by the
**§12.M AMENDMENT 2026-06-18 — Price Calculator forward-estimator rework
(founder-ratified)**.

Forward estimator (§12.M)
-------------------------
The seller enters a **Meesho Price** (the listed price); the backend
estimates the **net payout**.  Profit and margin are *outputs*, never
inputs.  ``target_margin_pct`` is removed; ``commission_pct`` is a
**seller input** (default 4%), NOT a per-category lookup.

Public surface
--------------
* :func:`calculate` — main endpoint surface (forward estimator).
* :func:`get_last_calc` — cross-module read (dashboard OPTIONAL per §13;
  V1 dashboard does NOT call this).

Cross-module imports (strict allowlist per §3.G + §16)
------------------------------------------------------
This module imports ``from app.modules.catalog import service`` ONLY (the
``assert_product_ownership`` gate).  Per §12.M the ``category`` commission
import is RETIRED.  It NEVER imports ``app.adapters.gemini`` — pricing is
deterministic math.

HARD RULE (§12.M (6))
---------------------
The production estimator makes ZERO Meesho/supplier calls — it is pure
arithmetic.  The scraped settlement artifacts used to calibrate it are
referenced ONLY in ``tests/modules/pricing/test_estimator_calibration.py``
and never under ``app/`` (a CI grep gate enforces this).

Calibration (§12.M (1))
-----------------------
The named constants below are calibrated against the real scraped
settlement sample ``meesho_price=106 → estimated_payout≈47``.  With the
defaults below the estimator yields ``106 → 46.84`` (residual −0.16) and
the WDRP band ``86 → 27.98`` (residual +0.98) — both inside the test
``TOLERANCE = Decimal("3.00")``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import ROUND_HALF_EVEN, Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import service as catalog_service
from app.modules.pricing import repository as pricing_repo
from app.modules.pricing.domain import PnLBreakdown, PricingAlert, PricingCalc
from app.modules.pricing.schemas import (
    PriceCalcAlert,
    PriceCalcRequest,
    PriceCalcResponse,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Named constants (§12.M (1)) — calibrated to ₹106 → ₹47
# ─────────────────────────────────────────────────────────────────────────────
_HUNDRED = Decimal("100")
_TWO_PLACES = Decimal("0.01")
"""Quantization template — 2 dp, banker's rounding (``ROUND_HALF_EVEN``)."""

# Shipping is bracketed by price band.
SHIPPING_BRACKET: Decimal = Decimal("1000")
"""Price threshold (INR) separating the low and high shipping bands."""
SHIPPING_FLAT: Decimal = Decimal("30")
"""<calibration> Shipping (INR) for ``meesho_price <= SHIPPING_BRACKET``.
Tuned so the estimator reproduces the real sample ₹106 → ₹47."""
SHIPPING_HIGH: Decimal = Decimal("70")
"""Shipping (INR) for ``meesho_price > SHIPPING_BRACKET`` — Meesho's
standard ₹70 forward shipping for higher-value parcels."""

DEFAULT_COMMISSION_PCT: Decimal = Decimal("4")
"""Seller-input default referral commission % (§12.M (2))."""
DEFAULT_GST_PCT: Decimal = Decimal("18")
"""GST % charged on the FEES (not on MRP)."""
DEFAULT_TCS_PCT: Decimal = Decimal("1")
"""Tax-collected-at-source % on the Meesho price."""
DEFAULT_TDS_PCT: Decimal = Decimal("0")
"""Tax-deducted-at-source % on the Meesho price (0 by default in V1)."""

DEFAULT_LOGISTICS_FEE: Decimal = Decimal("10")
"""<calibration> Logistics fee (INR) — tuned to the ₹106 → ₹47 sample."""
DEFAULT_FIXED_FEE: Decimal = Decimal("5")
"""<calibration> Fixed/closing fee (INR) — tuned to the ₹106 → ₹47 sample."""

WDRP_DELTA: Decimal = Decimal("20")
"""Wrong/Defective Return Price offset (INR): ``wdrp_price = meesho_price
− WDRP_DELTA``.  Reconciled against the real sample (wdrp 86 vs meesho
106 ≈ ₹20)."""

# Alert thresholds (§12.M (3)).
_LOW_MARGIN_THRESHOLD_PCT: Decimal = Decimal("10")
"""``margin_pct < 10`` → ``LOW_MARGIN``."""
_SHIPPING_DOMINATES_FRACTION: Decimal = Decimal("0.40")
"""``shipping > 40% of total_deductions`` → ``SHIPPING_DOMINATES``."""


# ─────────────────────────────────────────────────────────────────────────────
# Public — route-internal
# ─────────────────────────────────────────────────────────────────────────────
async def calculate(
    user_id: UUID,
    product_id: UUID,
    request: PriceCalcRequest,
    *,
    db: AsyncSession,
) -> PriceCalcResponse:
    """Main endpoint surface — forward payout estimator per §12.M.

    Steps:
      1. Assert product ownership (cross-module via catalog).
      2. Estimate the payout deterministically (no I/O, no Meesho calls).
      3. Estimate the WDRP-band payout.
      4. Generate alerts from the breakdown.
      5. Persist to ``pricing_calcs`` (append-only audit row).
      6. Return the wire-shape response.

    Raises:
        ProductNotFoundError: from
            :func:`catalog.service.assert_product_ownership` (404).
        InvalidPriceInputError: for malformed cross-field input (400).

    A negative ``estimated_payout`` does NOT raise — it returns 200 with a
    ``NEGATIVE_PAYOUT`` alert (§12.M (4)).
    """
    # Step 1 — cross-module ownership gate (M6).
    await catalog_service.assert_product_ownership(product_id, user_id, db=db)

    # Resolve the seller-entered + tunable estimator inputs.
    commission_pct = request.commission_pct
    gst_pct = request.override_gst_pct if request.override_gst_pct is not None else DEFAULT_GST_PCT
    tcs_pct = request.override_tcs_pct if request.override_tcs_pct is not None else DEFAULT_TCS_PCT
    tds_pct = request.override_tds_pct if request.override_tds_pct is not None else DEFAULT_TDS_PCT
    logistics_fee = (
        request.override_logistics_fee
        if request.override_logistics_fee is not None
        else DEFAULT_LOGISTICS_FEE
    )
    fixed_fee = (
        request.override_fixed_fee
        if request.override_fixed_fee is not None
        else DEFAULT_FIXED_FEE
    )

    # Step 2 — forward estimator for the listed Meesho price.
    breakdown = _estimate_payout(
        meesho_price=request.meesho_price,
        input_cost=request.input_cost,
        commission_pct=commission_pct,
        return_rate_pct=request.return_rate_pct,
        gst_pct=gst_pct,
        tcs_pct=tcs_pct,
        tds_pct=tds_pct,
        logistics_fee=logistics_fee,
        fixed_fee=fixed_fee,
        override_shipping=request.override_shipping,
    )

    # Step 3 — WDRP-band payout (re-run the estimator on the lower price).
    wdrp_price = _q(request.meesho_price - WDRP_DELTA)
    wdrp_breakdown = _estimate_payout(
        meesho_price=wdrp_price,
        input_cost=request.input_cost,
        commission_pct=commission_pct,
        return_rate_pct=request.return_rate_pct,
        gst_pct=gst_pct,
        tcs_pct=tcs_pct,
        tds_pct=tds_pct,
        logistics_fee=logistics_fee,
        fixed_fee=fixed_fee,
        override_shipping=request.override_shipping,
    )

    # Step 4 — alerts from the deterministic breakdown.
    alerts = _generate_alerts(breakdown)

    # Step 5 — append-only audit row.
    persisted = await pricing_repo.insert_calc(
        db,
        product_id=product_id,
        mrp=request.mrp,
        meesho_price=breakdown.meesho_price,
        estimated_payout=breakdown.estimated_payout,
        commission_pct=breakdown.commission_pct,
        gst_pct=breakdown.gst_pct,
        margin=breakdown.profit,
        margin_pct=breakdown.margin_pct,
        markup_pct=breakdown.markup_pct,
        referral_commission=breakdown.referral_commission,
        shipping_charge=breakdown.shipping_charge,
        logistics_fee=breakdown.logistics_fee,
        fixed_fee=breakdown.fixed_fee,
        gst_on_fees=breakdown.gst_on_fees,
        tcs=breakdown.tcs,
        tds=breakdown.tds,
        rto_expected_loss=breakdown.rto_expected_loss,
        return_rate_pct=breakdown.return_rate_pct,
        wdrp_price=wdrp_price,
    )

    # Step 6 — compose wire response.
    return PriceCalcResponse(
        mrp=request.mrp,
        meesho_price=breakdown.meesho_price,
        wdrp_price=wdrp_price,
        input_cost=breakdown.input_cost,
        commission_pct=breakdown.commission_pct,
        referral_commission=breakdown.referral_commission,
        shipping_charge=breakdown.shipping_charge,
        logistics_fee=breakdown.logistics_fee,
        fixed_fee=breakdown.fixed_fee,
        gst_pct=breakdown.gst_pct,
        gst_on_fees=breakdown.gst_on_fees,
        tcs=breakdown.tcs,
        tds=breakdown.tds,
        return_rate_pct=breakdown.return_rate_pct,
        rto_expected_loss=breakdown.rto_expected_loss,
        total_deductions=breakdown.total_deductions,
        estimated_payout=breakdown.estimated_payout,
        estimated_payout_wdrp=wdrp_breakdown.estimated_payout,
        profit=breakdown.profit,
        margin_pct=breakdown.margin_pct,
        markup_pct=breakdown.markup_pct,
        alerts=[
            PriceCalcAlert(
                code=a.code,
                message_id=a.message_id,
                severity=a.severity,
            )
            for a in alerts
        ],
        calculated_at=persisted.created_at or datetime.now(timezone.utc),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public — cross-module surface (§13 OPTIONAL)
# ─────────────────────────────────────────────────────────────────────────────
async def get_last_calc(
    user_id: UUID,
    product_id: UUID,
    *,
    db: AsyncSession,
) -> PricingCalc | None:
    """Return the most recent ``pricing_calcs`` row for ``product_id`` or
    ``None`` if no calc has been run yet.

    Consumed by ``dashboard.service.summary`` per §13 (OPTIONAL).  V1
    dashboard does NOT call this.  Tenancy enforced twice: service-layer
    ownership assert + repository-layer JOIN through ``products``.
    """
    await catalog_service.assert_product_ownership(product_id, user_id, db=db)
    return await pricing_repo.find_latest_by_product(db, user_id, product_id)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers — pure functions, unit-tested in isolation
# ─────────────────────────────────────────────────────────────────────────────
def _bracketed_shipping(meesho_price: Decimal) -> Decimal:
    """Bracketed flat shipping per the §12.M (1) price band:
    ``SHIPPING_FLAT`` when ``meesho_price <= SHIPPING_BRACKET`` else
    ``SHIPPING_HIGH``."""
    if meesho_price <= SHIPPING_BRACKET:
        return SHIPPING_FLAT
    return SHIPPING_HIGH


def _estimate_payout(
    *,
    meesho_price: Decimal,
    input_cost: Decimal,
    commission_pct: Decimal = DEFAULT_COMMISSION_PCT,
    return_rate_pct: Decimal = Decimal("0"),
    gst_pct: Decimal = DEFAULT_GST_PCT,
    tcs_pct: Decimal = DEFAULT_TCS_PCT,
    tds_pct: Decimal = DEFAULT_TDS_PCT,
    logistics_fee: Decimal = DEFAULT_LOGISTICS_FEE,
    fixed_fee: Decimal = DEFAULT_FIXED_FEE,
    override_shipping: Decimal | None = None,
) -> PnLBreakdown:
    """The locked forward estimator per §12.M (1).

    Deterministic, pure function, NO side effects, NO DB, NO I/O, NO
    Meesho calls.  All monetary values quantize to 2 dp via banker's
    rounding (``ROUND_HALF_EVEN``).

    Formula::

        referral_commission = meesho_price × commission_pct / 100
        shipping            = bracketed flat (override if supplied)
        fee_base            = referral + shipping + logistics + fixed
        gst_on_fees         = fee_base × gst_pct / 100   (GST on FEES, not MRP)
        tcs                 = meesho_price × tcs_pct / 100
        tds                 = meesho_price × tds_pct / 100
        rto_expected_loss   = return_rate_pct / 100 × (shipping + logistics)
        total_deductions    = referral + shipping + logistics + fixed
                              + gst_on_fees + tcs + tds + rto_expected_loss
        estimated_payout    = meesho_price − total_deductions
        profit              = estimated_payout − input_cost
        margin_pct          = profit / meesho_price × 100   (0 when price == 0)
        markup_pct          = profit / input_cost × 100     (0 when cost == 0)

    Calibrated to the real scraped sample ``meesho_price=106 → ≈47``.
    """
    referral_commission = _q(meesho_price * commission_pct / _HUNDRED)
    shipping = override_shipping if override_shipping is not None else _bracketed_shipping(meesho_price)
    fee_base = referral_commission + shipping + logistics_fee + fixed_fee
    gst_on_fees = _q(fee_base * gst_pct / _HUNDRED)
    tcs = _q(meesho_price * tcs_pct / _HUNDRED)
    tds = _q(meesho_price * tds_pct / _HUNDRED)
    rto_expected_loss = _q(return_rate_pct / _HUNDRED * (shipping + logistics_fee))

    total_deductions = _q(
        referral_commission
        + shipping
        + logistics_fee
        + fixed_fee
        + gst_on_fees
        + tcs
        + tds
        + rto_expected_loss
    )
    estimated_payout = _q(meesho_price - total_deductions)
    profit = _q(estimated_payout - input_cost)

    margin_pct = (
        _q(profit / meesho_price * _HUNDRED) if meesho_price > Decimal("0") else Decimal("0.00")
    )
    markup_pct = (
        _q(profit / input_cost * _HUNDRED) if input_cost > Decimal("0") else Decimal("0.00")
    )

    return PnLBreakdown(
        meesho_price=_q(meesho_price),
        input_cost=_q(input_cost),
        commission_pct=_q(commission_pct),
        referral_commission=referral_commission,
        shipping_charge=_q(shipping),
        logistics_fee=_q(logistics_fee),
        fixed_fee=_q(fixed_fee),
        gst_pct=_q(gst_pct),
        gst_on_fees=gst_on_fees,
        tcs=tcs,
        tds=tds,
        return_rate_pct=_q(return_rate_pct),
        rto_expected_loss=rto_expected_loss,
        total_deductions=total_deductions,
        estimated_payout=estimated_payout,
        profit=profit,
        margin_pct=margin_pct,
        markup_pct=markup_pct,
    )


def _generate_alerts(breakdown: PnLBreakdown) -> list[PricingAlert]:
    """Apply the 3 locked alert rules per §12.M (3) to the breakdown.

    Pure function — no side effects, no I/O.  Multiple alerts may fire
    simultaneously.
    """
    alerts: list[PricingAlert] = []

    # Rule 1 — NEGATIVE_PAYOUT: estimated payout strictly below zero.
    if breakdown.estimated_payout < Decimal("0"):
        alerts.append(
            PricingAlert(
                code="NEGATIVE_PAYOUT",
                message_id="pricing.alert.negative_payout",
                severity="warning",
            )
        )

    # Rule 2 — LOW_MARGIN: margin_pct strictly less than 10.
    if breakdown.margin_pct < _LOW_MARGIN_THRESHOLD_PCT:
        alerts.append(
            PricingAlert(
                code="LOW_MARGIN",
                message_id="pricing.alert.low_margin",
                severity="warning",
            )
        )

    # Rule 3 — SHIPPING_DOMINATES: shipping > 40% of total deductions.
    if breakdown.total_deductions > Decimal("0"):
        shipping_fraction = breakdown.shipping_charge / breakdown.total_deductions
        if shipping_fraction > _SHIPPING_DOMINATES_FRACTION:
            alerts.append(
                PricingAlert(
                    code="SHIPPING_DOMINATES",
                    message_id="pricing.alert.shipping_dominates",
                    severity="info",
                )
            )

    return alerts


def _q(value: Decimal) -> Decimal:
    """Quantize a Decimal to 2 dp with banker's rounding
    (``ROUND_HALF_EVEN``).  Centralised so every monetary surface rounds
    identically per the §12.M lock + CLAUDE.md numeric precision rule."""
    return value.quantize(_TWO_PLACES, rounding=ROUND_HALF_EVEN)


__all__ = [
    "calculate",
    "get_last_calc",
    # Pure-function exports for unit-tests (NOT part of the cross-module
    # surface — §16 callers must use ``calculate`` / ``get_last_calc``).
    "_estimate_payout",
    "_generate_alerts",
    "_bracketed_shipping",
    "DEFAULT_COMMISSION_PCT",
    "DEFAULT_GST_PCT",
    "DEFAULT_TCS_PCT",
    "DEFAULT_TDS_PCT",
    "DEFAULT_LOGISTICS_FEE",
    "DEFAULT_FIXED_FEE",
    "SHIPPING_FLAT",
    "SHIPPING_HIGH",
    "SHIPPING_BRACKET",
    "WDRP_DELTA",
]
