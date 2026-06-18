"""Pricing-module calibration test — forward payout estimator.

Per BACKEND_ARCHITECTURE.md §12.M AMENDMENT 2026-06-18 (founder-ratified).

Calibration source
-------------------
The forward estimator is calibrated against a real scraped Meesho
settlement sample:

    Meesho price (transfer_price observed) = ₹106  →  net payout ≈ ₹47
    WDRP (wrong/defective return price)     = ₹86   →  payout    ≈ ₹27

This is the ONLY file in the codebase that names the scraped artifacts
(``transfer_price`` / ``fetch-supplier-products`` / ``supplier.meesho.com``)
per the §12.M (6) HARD RULE: the production estimator makes ZERO Meesho
calls; those artifacts are calibration-only and never appear under
``backend/app/``.

Chosen calibration constants (tuned so the asserts below pass)
-------------------------------------------------------------
    SHIPPING_FLAT          = Decimal("30")   # low band (price <= 1000)
    SHIPPING_HIGH          = Decimal("70")   # high band (price > 1000)
    SHIPPING_BRACKET       = Decimal("1000")
    DEFAULT_LOGISTICS_FEE  = Decimal("10")
    DEFAULT_FIXED_FEE      = Decimal("5")
    DEFAULT_COMMISSION_PCT = Decimal("4")
    DEFAULT_GST_PCT        = Decimal("18")   # GST on fees
    DEFAULT_TCS_PCT        = Decimal("1")
    DEFAULT_TDS_PCT        = Decimal("0")
    WDRP_DELTA             = Decimal("20")

Residuals (within TOLERANCE = Decimal("3.00"))
----------------------------------------------
    estimate(106) = 46.84   →   residual vs 47 = -0.16
    estimate(86)  = 27.98   →   residual vs 27 = +0.98
"""

from __future__ import annotations

from decimal import Decimal

import pytest

# NOTE: ``transfer_price`` / ``fetch-supplier-products`` / ``supplier.meesho.com``
# below are CALIBRATION-ONLY references to the scraped sample.  They MUST NOT
# appear under backend/app/ (§12.M (6) HARD RULE; enforced by the CI grep gate).
from app.modules.pricing.service import (
    DEFAULT_COMMISSION_PCT,
    DEFAULT_GST_PCT,
    DEFAULT_TCS_PCT,
    SHIPPING_FLAT,
    SHIPPING_HIGH,
    WDRP_DELTA,
    _estimate_payout,
)

pytestmark = pytest.mark.unit

TOLERANCE = Decimal("3.00")

# The real scraped settlement sample (calibration source). ``transfer_price``
# is the supplier-side value observed via a historical fetch-supplier-products
# scrape against supplier.meesho.com — used ONLY here for calibration.
SAMPLE_MEESHO_PRICE = Decimal("106")
SAMPLE_EXPECTED_PAYOUT = Decimal("47")
SAMPLE_WDRP_PRICE = Decimal("86")
SAMPLE_WDRP_EXPECTED_PAYOUT = Decimal("27")


class TestEstimatorCalibration:
    """The forward estimator reproduces the real scraped sample."""

    def test_reproduces_106_to_47_within_tolerance(self):
        """``_estimate_payout(meesho_price=106, defaults)`` ≈ 47 ± 3.00."""
        breakdown = _estimate_payout(
            meesho_price=SAMPLE_MEESHO_PRICE,
            input_cost=Decimal("40"),
            commission_pct=DEFAULT_COMMISSION_PCT,
            gst_pct=DEFAULT_GST_PCT,
            tcs_pct=DEFAULT_TCS_PCT,
        )
        residual = breakdown.estimated_payout - SAMPLE_EXPECTED_PAYOUT
        assert abs(residual) <= TOLERANCE, (
            f"calibration drift: estimate(106)={breakdown.estimated_payout}, "
            f"expected≈{SAMPLE_EXPECTED_PAYOUT}, residual={residual} "
            f"(tolerance ±{TOLERANCE})"
        )

    def test_wdrp_band_86_to_27_within_tolerance(self):
        """The WDRP band ``86 → ≈27`` within tolerance.

        ``wdrp_price = meesho_price − WDRP_DELTA = 106 − 20 = 86``.
        """
        assert SAMPLE_MEESHO_PRICE - WDRP_DELTA == SAMPLE_WDRP_PRICE
        breakdown = _estimate_payout(
            meesho_price=SAMPLE_WDRP_PRICE,
            input_cost=Decimal("40"),
            commission_pct=DEFAULT_COMMISSION_PCT,
            gst_pct=DEFAULT_GST_PCT,
            tcs_pct=DEFAULT_TCS_PCT,
        )
        residual = breakdown.estimated_payout - SAMPLE_WDRP_EXPECTED_PAYOUT
        assert abs(residual) <= TOLERANCE, (
            f"WDRP calibration drift: estimate(86)={breakdown.estimated_payout}, "
            f"expected≈{SAMPLE_WDRP_EXPECTED_PAYOUT}, residual={residual} "
            f"(tolerance ±{TOLERANCE})"
        )

    def test_low_price_crush_deductions_exceed_half(self):
        """Low-price-crush: at ₹106 the deduction stack exceeds 50% of the
        Meesho price, demonstrating why low-priced SKUs are unprofitable on
        Meesho once shipping + fees are charged."""
        breakdown = _estimate_payout(
            meesho_price=SAMPLE_MEESHO_PRICE,
            input_cost=Decimal("40"),
        )
        half_price = SAMPLE_MEESHO_PRICE / Decimal("2")
        assert breakdown.total_deductions > half_price, (
            f"expected deductions > 50% of ₹106 (₹{half_price}); "
            f"got deductions=₹{breakdown.total_deductions}"
        )

    def test_shipping_bracket_low_band(self):
        """``meesho_price <= SHIPPING_BRACKET`` → ``SHIPPING_FLAT`` shipping."""
        breakdown = _estimate_payout(
            meesho_price=Decimal("106"),
            input_cost=Decimal("40"),
        )
        assert breakdown.shipping_charge == SHIPPING_FLAT

    def test_shipping_bracket_high_band(self):
        """``meesho_price > SHIPPING_BRACKET`` → ``SHIPPING_HIGH`` shipping."""
        breakdown = _estimate_payout(
            meesho_price=Decimal("1500"),
            input_cost=Decimal("400"),
        )
        assert breakdown.shipping_charge == SHIPPING_HIGH

    def test_all_monetary_fields_are_decimal_two_places(self):
        """Every monetary surface ships as ``Decimal`` quantized to 2 dp."""
        breakdown = _estimate_payout(
            meesho_price=Decimal("106"),
            input_cost=Decimal("40"),
        )
        fields = [
            breakdown.meesho_price,
            breakdown.input_cost,
            breakdown.referral_commission,
            breakdown.shipping_charge,
            breakdown.logistics_fee,
            breakdown.fixed_fee,
            breakdown.gst_on_fees,
            breakdown.tcs,
            breakdown.tds,
            breakdown.rto_expected_loss,
            breakdown.total_deductions,
            breakdown.estimated_payout,
            breakdown.profit,
            breakdown.margin_pct,
            breakdown.markup_pct,
        ]
        for value in fields:
            assert isinstance(value, Decimal), f"non-Decimal value: {value!r}"
            assert -value.as_tuple().exponent == 2, (
                f"value not quantized to 2 dp: {value!r}"
            )
