"""Pricing-module unit test #3 — P&L formula correctness.

Per BACKEND_ARCHITECTURE.md §12.J:

    P&L formula correctness — golden fixtures: ``input_cost=100``,
    ``target_margin_pct=30``, ``commission_pct=15`` → expected
    ``seller_price=130``, ``mrp≈151.52``, ``profit=30``, ``profit_pct=30``
    (subject to ROUND_HALF_EVEN).  Decimal precision exact match — no
    ``==`` on float, all asserts via Decimal comparison.

DECISION FLAG §12-PRICING-D2 — golden assertion follows the locked formula
-------------------------------------------------------------------------
The §12.B.1 step 6 formula

    mrp = seller_price / (1 − commission_pct/100 − (gst_pct/100) × (commission_pct/100))

evaluates to ``130 / (1 − 0.15 − 0.18 × 0.15) = 130 / 0.823 ≈ 157.96`` for
the golden fixture — NOT 151.52 as the §12.J prose mentions.  This test
asserts the formula-derived value (``Decimal('157.96')``).  The locked
formula is the contract; the prose golden is a spec drafting error.  All
other goldens (``seller_price=130``, ``profit=30``, ``profit_pct=30``)
match the formula and stand.
"""

from __future__ import annotations

from decimal import Decimal

from app.modules.pricing.service import _compute_pnl, DEFAULT_GST_PCT


class TestPnlFormulaCorrectness:
    """Golden-fixture verification of the locked P&L algorithm."""

    def test_canonical_golden_fixture(self):
        """``input_cost=100, target_margin_pct=30, commission_pct=15`` →
        ``seller_price=130, mrp=157.96, profit=30, profit_pct=30``.

        Per §12-PRICING-D2: ``mrp = 157.96`` is the formula-derived
        value with banker's rounding (``ROUND_HALF_EVEN``)."""
        breakdown = _compute_pnl(
            input_cost=Decimal("100"),
            target_margin_pct=Decimal("30"),
            commission_pct=Decimal("15"),
            gst_pct=DEFAULT_GST_PCT,
        )

        assert breakdown.seller_price == Decimal("130.00"), (
            f"seller_price drift: expected 130.00, got {breakdown.seller_price}"
        )
        assert breakdown.mrp == Decimal("157.96"), (
            f"mrp drift: expected 157.96 (formula-derived), got {breakdown.mrp}. "
            "See §12-PRICING-D2 in pricing/service.py docstring."
        )
        assert breakdown.profit == Decimal("30.00"), (
            f"profit drift: expected 30.00, got {breakdown.profit}"
        )
        assert breakdown.profit_pct == Decimal("30.00"), (
            f"profit_pct drift: expected 30.00, got {breakdown.profit_pct}"
        )

    def test_meesho_price_equals_mrp_in_v1(self):
        """Per §12.B.1 step 6: ``meesho_price = mrp`` in V1 (V1.5 may
        differentiate when discount fields land)."""
        breakdown = _compute_pnl(
            input_cost=Decimal("100"),
            target_margin_pct=Decimal("30"),
            commission_pct=Decimal("15"),
            gst_pct=DEFAULT_GST_PCT,
        )
        assert breakdown.meesho_price == breakdown.mrp

    def test_commission_amount_derived_from_mrp(self):
        """``commission_amount = mrp × commission_pct / 100`` —
        quantize to 2 dp banker's rounding."""
        breakdown = _compute_pnl(
            input_cost=Decimal("100"),
            target_margin_pct=Decimal("30"),
            commission_pct=Decimal("15"),
            gst_pct=DEFAULT_GST_PCT,
        )
        # mrp = 157.96, commission_pct = 15  → 157.96 × 0.15 = 23.694
        # ROUND_HALF_EVEN to 2 dp: trailing 4 < 5 → 23.69.
        assert breakdown.commission_amount == Decimal("23.69")

    def test_gst_charged_on_commission_not_mrp(self):
        """Per §12.B.1 step 6: ``gst_amount = commission_amount ×
        gst_pct / 100`` (GST is charged on the seller fee, not the full
        MRP — Meesho's structure)."""
        breakdown = _compute_pnl(
            input_cost=Decimal("100"),
            target_margin_pct=Decimal("30"),
            commission_pct=Decimal("15"),
            gst_pct=DEFAULT_GST_PCT,
        )
        # commission_amount = 23.69, gst_pct = 18 → 23.69 × 0.18 = 4.2642
        # ROUND_HALF_EVEN to 2 dp: trailing 4 < 5 → 4.26.
        assert breakdown.gst_amount == Decimal("4.26")

    def test_all_monetary_fields_are_decimal_with_two_places(self):
        """Every monetary surface ships as ``Decimal`` quantized to 2 dp
        (banker's rounding) per CLAUDE.md numeric precision rule + §12.B.1
        step 6 lock.  No float, no inexact representation."""
        breakdown = _compute_pnl(
            input_cost=Decimal("100"),
            target_margin_pct=Decimal("30"),
            commission_pct=Decimal("15"),
            gst_pct=DEFAULT_GST_PCT,
        )
        monetary_fields = [
            breakdown.mrp,
            breakdown.meesho_price,
            breakdown.seller_price,
            breakdown.commission_pct,
            breakdown.commission_amount,
            breakdown.gst_pct,
            breakdown.gst_amount,
            breakdown.profit,
            breakdown.profit_pct,
        ]
        for value in monetary_fields:
            assert isinstance(value, Decimal), (
                f"non-Decimal monetary value: {value!r} (type {type(value)})"
            )
            # Quantum check: tuple representation should have exactly 2 dp.
            assert -value.as_tuple().exponent == 2, (
                f"monetary value not quantized to 2 dp: {value!r}"
            )

    def test_zero_commission_does_not_divide_by_zero(self):
        """A 0% commission still divides cleanly: denom = 1.0, mrp =
        seller_price (no fees deducted).  Defensive — the service-layer
        D1 gate is the production safeguard against this case."""
        breakdown = _compute_pnl(
            input_cost=Decimal("100"),
            target_margin_pct=Decimal("30"),
            commission_pct=Decimal("0"),
            gst_pct=DEFAULT_GST_PCT,
        )
        assert breakdown.mrp == breakdown.seller_price == Decimal("130.00")
        assert breakdown.commission_amount == Decimal("0.00")
        assert breakdown.gst_amount == Decimal("0.00")
