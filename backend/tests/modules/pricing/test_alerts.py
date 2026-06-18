"""Pricing-module unit test — Alert generation (forward estimator).

Per BACKEND_ARCHITECTURE.md §12.M (3) AMENDMENT 2026-06-18.

Locked alert rules:
    * ``NEGATIVE_PAYOUT``    — ``estimated_payout < 0``                 — warning
    * ``LOW_MARGIN``         — ``margin_pct < 10``                     — warning
    * ``SHIPPING_DOMINATES`` — ``shipping > 40% of total_deductions``  — info

All thresholds are strict inequalities.  Multiple alerts may fire.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.pricing.service import _estimate_payout, _generate_alerts

pytestmark = pytest.mark.unit


def _codes(alerts) -> set[str]:
    return {a.code for a in alerts}


class TestAlertGeneration:
    """Forward-estimator alert rules per §12.M (3)."""

    def test_negative_payout_fires_warning(self):
        """A price below the deduction floor → ``NEGATIVE_PAYOUT`` warning.

        ``meesho_price=20`` (very low) → payout negative.
        """
        breakdown = _estimate_payout(
            meesho_price=Decimal("20"),
            input_cost=Decimal("40"),
        )
        alerts = _generate_alerts(breakdown)
        codes = _codes(alerts)
        assert "NEGATIVE_PAYOUT" in codes, (
            f"payout={breakdown.estimated_payout} should fire NEGATIVE_PAYOUT; "
            f"got {codes}"
        )
        neg = next(a for a in alerts if a.code == "NEGATIVE_PAYOUT")
        assert neg.severity == "warning"
        assert neg.message_id == "pricing.alert.negative_payout"

    def test_low_margin_fires_warning(self):
        """``margin_pct < 10`` → ``LOW_MARGIN`` warning.

        ``meesho_price=106, input_cost=44`` → payout 46.84, profit 2.84,
        margin_pct ≈ 2.68 (< 10) → LOW_MARGIN.
        """
        breakdown = _estimate_payout(
            meesho_price=Decimal("106"),
            input_cost=Decimal("44"),
        )
        alerts = _generate_alerts(breakdown)
        codes = _codes(alerts)
        assert "LOW_MARGIN" in codes, (
            f"margin_pct={breakdown.margin_pct} should fire LOW_MARGIN; got {codes}"
        )
        low = next(a for a in alerts if a.code == "LOW_MARGIN")
        assert low.severity == "warning"
        assert low.message_id == "pricing.alert.low_margin"

    def test_shipping_dominates_fires_info(self):
        """``shipping > 40% of total_deductions`` → ``SHIPPING_DOMINATES``.

        At ₹106 with default deductions shipping=30 of total≈59.16 → ~51% > 40%.
        """
        breakdown = _estimate_payout(
            meesho_price=Decimal("106"),
            input_cost=Decimal("40"),
        )
        alerts = _generate_alerts(breakdown)
        codes = _codes(alerts)
        assert "SHIPPING_DOMINATES" in codes, (
            f"shipping={breakdown.shipping_charge} of total="
            f"{breakdown.total_deductions} should fire SHIPPING_DOMINATES; got {codes}"
        )
        ship = next(a for a in alerts if a.code == "SHIPPING_DOMINATES")
        assert ship.severity == "info"
        assert ship.message_id == "pricing.alert.shipping_dominates"

    def test_healthy_high_price_calc_fires_no_alerts(self):
        """A healthy high-value calc fires no alerts.

        ``meesho_price=5000, input_cost=2000`` → payout well above cost,
        margin comfortably ≥ 10, shipping (70) a small slice of total.
        """
        breakdown = _estimate_payout(
            meesho_price=Decimal("5000"),
            input_cost=Decimal("2000"),
        )
        alerts = _generate_alerts(breakdown)
        assert alerts == [], f"healthy calc should fire no alerts; got {_codes(alerts)}"

    def test_negative_payout_implies_low_margin_too(self):
        """When payout is negative, margin_pct is also negative (< 10), so
        BOTH ``NEGATIVE_PAYOUT`` and ``LOW_MARGIN`` fire."""
        breakdown = _estimate_payout(
            meesho_price=Decimal("20"),
            input_cost=Decimal("40"),
        )
        codes = _codes(_generate_alerts(breakdown))
        assert {"NEGATIVE_PAYOUT", "LOW_MARGIN"}.issubset(codes)

    def test_retired_alert_codes_never_appear(self):
        """The retired ``HIGH_MRP_MULTIPLIER`` / ``THIN_PROFIT`` codes are
        never emitted (§12.M (3))."""
        breakdown = _estimate_payout(
            meesho_price=Decimal("106"),
            input_cost=Decimal("44"),
        )
        codes = _codes(_generate_alerts(breakdown))
        assert "HIGH_MRP_MULTIPLIER" not in codes
        assert "THIN_PROFIT" not in codes
