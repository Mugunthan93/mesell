"""Pricing-module unit test #4 — Alert generation.

Per BACKEND_ARCHITECTURE.md §12.J:

  Alert generation — three sub-cases:
    * low-margin scenario → alerts includes ``LOW_MARGIN``.
    * high-mrp-multiplier scenario → alerts includes ``HIGH_MRP_MULTIPLIER``.
    * thin-profit scenario → alerts includes both ``THIN_PROFIT`` and
      ``LOW_MARGIN``.

Locked alert rules per §12.F + §12-PRICING-D2:
    * ``LOW_MARGIN``         — ``profit_pct < 10`` (strict)
    * ``HIGH_MRP_MULTIPLIER``— ``mrp / input_cost > 3`` (strict)
    * ``THIN_PROFIT``        — ``profit < 50`` INR (strict)

All thresholds are strict inequalities — at the boundary no alert fires.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

pytestmark = pytest.mark.unit

from app.modules.pricing.service import (
    DEFAULT_GST_PCT,
    _compute_pnl,
    _generate_alerts,
)


def _codes(alerts) -> set[str]:
    """Helper — extract the ``code`` set from a list of PricingAlert."""
    return {a.code for a in alerts}


class TestAlertGeneration:
    """Three sub-cases per §12.J test #4."""

    def test_low_margin_scenario_fires_low_margin(self):
        """``profit_pct < 10`` → ``LOW_MARGIN`` warning.

        Fixture: ``input_cost=200, target_margin_pct=5, commission_pct=15``.
        seller_price = 210, profit = 10, profit_pct = 5 → LOW_MARGIN.
        profit = 10 < 50 → THIN_PROFIT also fires.
        mrp/input = 210/0.823/200 ≈ 1.27 → no HIGH_MRP_MULTIPLIER.
        """
        breakdown = _compute_pnl(
            input_cost=Decimal("200"),
            target_margin_pct=Decimal("5"),
            commission_pct=Decimal("15"),
            gst_pct=DEFAULT_GST_PCT,
        )
        alerts = _generate_alerts(breakdown, input_cost=Decimal("200"))

        codes = _codes(alerts)
        assert "LOW_MARGIN" in codes, (
            f"profit_pct={breakdown.profit_pct} should trigger LOW_MARGIN; "
            f"got codes={codes}"
        )
        low_margin = next(a for a in alerts if a.code == "LOW_MARGIN")
        assert low_margin.severity == "warning"
        assert low_margin.message_id == "pricing.alert.low_margin"

    def test_high_mrp_multiplier_scenario_fires_high_mrp(self):
        """``mrp / input_cost > 3`` → ``HIGH_MRP_MULTIPLIER`` warning.

        Fixture: ``input_cost=10, target_margin_pct=200, commission_pct=15``.
        seller_price = 30, mrp = 30/0.823 ≈ 36.45.
        mrp/input = 3.645 > 3 → HIGH_MRP_MULTIPLIER fires.
        profit = 20 → also THIN_PROFIT and LOW_MARGIN? profit_pct = 200,
        not < 10 → no LOW_MARGIN.  profit=20 < 50 → THIN_PROFIT also fires.
        """
        breakdown = _compute_pnl(
            input_cost=Decimal("10"),
            target_margin_pct=Decimal("200"),
            commission_pct=Decimal("15"),
            gst_pct=DEFAULT_GST_PCT,
        )
        alerts = _generate_alerts(breakdown, input_cost=Decimal("10"))

        codes = _codes(alerts)
        assert "HIGH_MRP_MULTIPLIER" in codes, (
            f"mrp/input={breakdown.mrp / Decimal('10')} should trigger "
            f"HIGH_MRP_MULTIPLIER; got codes={codes}"
        )
        high = next(a for a in alerts if a.code == "HIGH_MRP_MULTIPLIER")
        assert high.severity == "warning"
        assert high.message_id == "pricing.alert.high_mrp_multiplier"
        # LOW_MARGIN should NOT fire — profit_pct is 200 in this scenario.
        assert "LOW_MARGIN" not in codes

    def test_thin_profit_scenario_fires_both_thin_and_low(self):
        """Per §12.J test #4 sub-case 3: thin-profit scenario where
        ``alerts`` includes BOTH ``THIN_PROFIT`` and ``LOW_MARGIN``.

        Fixture: ``input_cost=100, target_margin_pct=9, commission_pct=15``.
        seller_price = 109, profit = 9, profit_pct = 9.
        profit < 50 → THIN_PROFIT.
        profit_pct < 10 → LOW_MARGIN.
        mrp/input < 3 → no HIGH_MRP_MULTIPLIER.
        """
        breakdown = _compute_pnl(
            input_cost=Decimal("100"),
            target_margin_pct=Decimal("9"),
            commission_pct=Decimal("15"),
            gst_pct=DEFAULT_GST_PCT,
        )
        alerts = _generate_alerts(breakdown, input_cost=Decimal("100"))

        codes = _codes(alerts)
        assert {"THIN_PROFIT", "LOW_MARGIN"}.issubset(codes), (
            f"Expected both THIN_PROFIT and LOW_MARGIN; got codes={codes}"
        )
        thin = next(a for a in alerts if a.code == "THIN_PROFIT")
        assert thin.severity == "info"
        assert thin.message_id == "pricing.alert.thin_profit"

    def test_healthy_calc_fires_no_alerts(self):
        """A genuinely healthy calc fires no alerts.

        Fixture: ``input_cost=1000, target_margin_pct=50, commission_pct=15``.
        seller_price = 1500, profit = 500, profit_pct = 50.
        mrp = 1500/0.823 ≈ 1822.60. mrp/input = 1.82 < 3.
        profit_pct 50 ≥ 10; profit 500 ≥ 50 → no alerts.
        """
        breakdown = _compute_pnl(
            input_cost=Decimal("1000"),
            target_margin_pct=Decimal("50"),
            commission_pct=Decimal("15"),
            gst_pct=DEFAULT_GST_PCT,
        )
        alerts = _generate_alerts(breakdown, input_cost=Decimal("1000"))
        assert alerts == [], (
            f"Healthy calc should fire no alerts; got {_codes(alerts)}"
        )

    def test_boundary_at_low_margin_threshold_does_not_fire(self):
        """Threshold is STRICT (<10).  At profit_pct == 10 → no LOW_MARGIN.

        Fixture: ``input_cost=100, target_margin_pct=10, commission_pct=15``.
        seller_price = 110, profit = 10, profit_pct = 10.
        profit_pct = 10 → NOT < 10 → no LOW_MARGIN.
        profit = 10 < 50 → THIN_PROFIT still fires.
        """
        breakdown = _compute_pnl(
            input_cost=Decimal("100"),
            target_margin_pct=Decimal("10"),
            commission_pct=Decimal("15"),
            gst_pct=DEFAULT_GST_PCT,
        )
        alerts = _generate_alerts(breakdown, input_cost=Decimal("100"))
        codes = _codes(alerts)
        assert "LOW_MARGIN" not in codes
        assert "THIN_PROFIT" in codes
