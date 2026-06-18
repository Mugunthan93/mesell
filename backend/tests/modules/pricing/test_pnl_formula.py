"""Pricing-module unit test — forward estimator formula correctness.

Per BACKEND_ARCHITECTURE.md §12.M AMENDMENT 2026-06-18 (founder-ratified).

Verifies the deterministic forward estimator
:func:`app.modules.pricing.service._estimate_payout` term-by-term, plus
the derived ``profit`` / ``margin_pct`` / ``markup_pct`` outputs.  All
asserts via Decimal comparison — no ``==`` on float.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.pricing.service import (
    DEFAULT_COMMISSION_PCT,
    DEFAULT_FIXED_FEE,
    DEFAULT_GST_PCT,
    DEFAULT_LOGISTICS_FEE,
    DEFAULT_TCS_PCT,
    DEFAULT_TDS_PCT,
    SHIPPING_FLAT,
    _estimate_payout,
)

pytestmark = pytest.mark.unit


class TestForwardEstimatorFormula:
    """Term-by-term verification of the §12.M (1) estimator."""

    def test_referral_commission_from_meesho_price(self):
        """``referral_commission = meesho_price × commission_pct / 100``."""
        b = _estimate_payout(meesho_price=Decimal("106"), input_cost=Decimal("40"))
        # 106 × 4% = 4.24
        assert b.referral_commission == Decimal("4.24")
        assert b.commission_pct == DEFAULT_COMMISSION_PCT

    def test_shipping_is_bracketed_flat_low_band(self):
        """Low band (price ≤ 1000) → ``SHIPPING_FLAT``."""
        b = _estimate_payout(meesho_price=Decimal("106"), input_cost=Decimal("40"))
        assert b.shipping_charge == SHIPPING_FLAT

    def test_gst_charged_on_fees_not_on_mrp(self):
        """``gst_on_fees = (referral + shipping + logistics + fixed) × 18%``."""
        b = _estimate_payout(meesho_price=Decimal("106"), input_cost=Decimal("40"))
        fee_base = (
            b.referral_commission + b.shipping_charge + DEFAULT_LOGISTICS_FEE + DEFAULT_FIXED_FEE
        )
        expected_gst = (fee_base * DEFAULT_GST_PCT / Decimal("100")).quantize(Decimal("0.01"))
        assert b.gst_on_fees == expected_gst

    def test_tcs_and_tds_on_meesho_price(self):
        """``tcs = price × 1%``; ``tds = price × 0%`` (default)."""
        b = _estimate_payout(meesho_price=Decimal("106"), input_cost=Decimal("40"))
        assert b.tcs == Decimal("1.06")  # 106 × 1%
        assert b.tds == Decimal("0.00")  # default tds_pct = 0
        assert DEFAULT_TCS_PCT == Decimal("1")
        assert DEFAULT_TDS_PCT == Decimal("0")

    def test_rto_expected_loss_zero_when_no_returns(self):
        """``return_rate_pct = 0`` → ``rto_expected_loss = 0``."""
        b = _estimate_payout(meesho_price=Decimal("106"), input_cost=Decimal("40"))
        assert b.rto_expected_loss == Decimal("0.00")

    def test_rto_expected_loss_scales_with_return_rate(self):
        """``rto = return_rate% × (shipping + logistics)``."""
        b = _estimate_payout(
            meesho_price=Decimal("106"),
            input_cost=Decimal("40"),
            return_rate_pct=Decimal("10"),
        )
        expected = (
            Decimal("10") / Decimal("100") * (b.shipping_charge + DEFAULT_LOGISTICS_FEE)
        ).quantize(Decimal("0.01"))
        assert b.rto_expected_loss == expected

    def test_estimated_payout_is_price_minus_deductions(self):
        """``estimated_payout = meesho_price − total_deductions``."""
        b = _estimate_payout(meesho_price=Decimal("106"), input_cost=Decimal("40"))
        assert b.estimated_payout == (Decimal("106") - b.total_deductions).quantize(
            Decimal("0.01")
        )
        # Calibration sanity: 106 → 46.84.
        assert b.estimated_payout == Decimal("46.84")

    def test_profit_margin_and_markup_outputs(self):
        """``profit = payout − cost``; ``margin = profit/price``;
        ``markup = profit/cost``."""
        b = _estimate_payout(meesho_price=Decimal("106"), input_cost=Decimal("40"))
        assert b.profit == (b.estimated_payout - Decimal("40")).quantize(Decimal("0.01"))
        assert b.margin_pct == (b.profit / Decimal("106") * Decimal("100")).quantize(
            Decimal("0.01")
        )
        assert b.markup_pct == (b.profit / Decimal("40") * Decimal("100")).quantize(
            Decimal("0.01")
        )

    def test_margin_pct_zero_when_price_zero_guard(self):
        """Defensive guard: a zero price (bypassing the schema gate) yields
        ``margin_pct = 0`` rather than a ZeroDivisionError."""
        b = _estimate_payout(meesho_price=Decimal("0"), input_cost=Decimal("40"))
        assert b.margin_pct == Decimal("0.00")

    def test_markup_pct_zero_when_cost_zero_guard(self):
        """Defensive guard: a zero cost yields ``markup_pct = 0``."""
        b = _estimate_payout(meesho_price=Decimal("106"), input_cost=Decimal("0"))
        assert b.markup_pct == Decimal("0.00")

    def test_negative_payout_does_not_raise(self):
        """A crushingly-low price still computes (negative payout) — the
        service surfaces it as an alert, not an exception."""
        b = _estimate_payout(meesho_price=Decimal("20"), input_cost=Decimal("40"))
        assert b.estimated_payout < Decimal("0")
