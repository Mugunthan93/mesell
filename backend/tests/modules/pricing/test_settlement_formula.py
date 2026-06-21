"""Pricing-module unit tests — census-confirmed settlement formula.

Per W2 Price Calculator rework (census-confirmed settlement model,
2026-06-19) — authoritative source
``.claude/agent-memory/nexus-level-0-director/project_pricing_transfer_price_model.md``.

Verifies the deterministic settlement calculator
:func:`app.modules.pricing.service._compute_settlement` term-by-term plus
the single ``NEGATIVE_SETTLEMENT`` alert.  All asserts via Decimal
comparison — never ``==`` on float.

Golden anchors:
  * Real order — SKU TTC-BL-OR-HP-NG-P4 (founder's first actual payout):
    selling_price 70, hair-clip shipping 45 → estimated_bank_settlement 61.78.
  * Census sanity — sscat_id 10949 (Extension Chords):
    selling_price 100, shipping 82 → 85.06.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.pricing.service import _compute_settlement, _generate_alerts

pytestmark = pytest.mark.unit

_LOOKUP_FILE = (
    Path(__file__).resolve().parents[3] / "app" / "data" / "meesho_pricing_lookup.json"
)


class TestSettlementFormula:
    """Term-by-term verification of the confirmed settlement formula."""

    def test_real_order(self):
        """Founder's first real order reproduced to the paise.

        selling_price=70, shipping=45, commission_pct=0:
        gst_on_shipping = 0.18×45 = 8.10
        total_price     = 115.00
        tds             = 0.001×115 = 0.115 → 0.12 (ROUND_HALF_UP)
        settlement      = 70 − 0 − 8.10 − 0.12 − 0 = 61.78
        """
        b = _compute_settlement(
            selling_price=Decimal("70"), shipping=45, commission_pct=Decimal("0")
        )
        assert b.estimated_bank_settlement == Decimal("61.78")
        assert b.gst_on_shipping == Decimal("8.10")
        assert b.tds == Decimal("0.12")
        assert b.total_price == Decimal("115.00")
        assert b.commission_fees == Decimal("0.00")
        assert b.tcs == Decimal("0.00")
        assert b.shipping == Decimal("45.00")

    def test_census_sanity(self):
        """Census anchor sscat_id 10949 @ price 100, shipping 82."""
        b = _compute_settlement(
            selling_price=Decimal("100"), shipping=82, commission_pct=Decimal("0")
        )
        assert b.estimated_bank_settlement == Decimal("85.06")
        assert b.gst_on_shipping == Decimal("14.76")
        assert b.tds == Decimal("0.18")
        assert b.total_price == Decimal("182.00")

    def test_commission_override(self):
        """A 2% commission reduces settlement by exactly the commission_fees."""
        base = _compute_settlement(
            selling_price=Decimal("100"), shipping=82, commission_pct=Decimal("0")
        )
        with_comm = _compute_settlement(
            selling_price=Decimal("100"), shipping=82, commission_pct=Decimal("2")
        )
        assert with_comm.commission_fees == Decimal("2.00")
        assert (
            base.estimated_bank_settlement - with_comm.estimated_bank_settlement
            == Decimal("2.00")
        )

    def test_tcs_always_zero(self):
        """tcs is always 0.00 regardless of inputs."""
        for sp, ship in [("70", 45), ("100", 82), ("1", 8435), ("5000", 48)]:
            b = _compute_settlement(
                selling_price=Decimal(sp), shipping=ship, commission_pct=Decimal("0")
            )
            assert b.tcs == Decimal("0.00")

    def test_all_monetary_fields_two_places(self):
        """Every monetary field is a Decimal quantized to exactly 2 dp."""
        b = _compute_settlement(
            selling_price=Decimal("70"), shipping=45, commission_pct=Decimal("0")
        )
        for value in (
            b.selling_price,
            b.shipping,
            b.total_price,
            b.commission_pct,
            b.commission_fees,
            b.gst_on_shipping,
            b.tds,
            b.tcs,
            b.estimated_bank_settlement,
        ):
            assert isinstance(value, Decimal)
            assert value == value.quantize(Decimal("0.01"))


class TestCensusWide:
    """Self-consistent census reproduction across a wide sample of real ids.

    The shipped lookup carries each category's constant shipping charge; at
    price=100 / commission=0 the settlement equals the census
    ``transfer_price_at_100`` by construction.  This guards the formula
    against drift across the full shipping range (₹48–₹8,435).
    """

    def test_census_wide(self):
        lookup = json.loads(_LOOKUP_FILE.read_text(encoding="utf-8"))["lookup"]
        sample = list(lookup.items())[:80]
        assert len(sample) >= 50, "need N>=50 census anchors"
        for _leaf_id, row in sample:
            shipping = int(row["shipping_charges"])
            commission = Decimal(str(row["commission_percentage"]))
            b = _compute_settlement(
                selling_price=Decimal("100"),
                shipping=shipping,
                commission_pct=commission,
            )
            # transfer_price_at_100 = 100 − (0.18×shipping) − (0.001×182...)
            ship_q = Decimal(shipping).quantize(Decimal("0.01"))
            gst = (Decimal("0.18") * ship_q).quantize(Decimal("0.01"))
            tds = (Decimal("0.001") * (Decimal("100") + ship_q)).quantize(
                Decimal("0.01")
            )
            expected = (Decimal("100") - gst - tds).quantize(Decimal("0.01"))
            assert abs(b.estimated_bank_settlement - expected) <= Decimal("0.01")


class TestAlerts:
    """The single locked alert rule — NEGATIVE_SETTLEMENT."""

    def test_negative_settlement_fires_warning(self):
        """selling_price tiny vs shipping → settlement < 0 → one warning."""
        b = _compute_settlement(
            selling_price=Decimal("1"), shipping=8435, commission_pct=Decimal("0")
        )
        assert b.estimated_bank_settlement < Decimal("0")
        alerts = _generate_alerts(b)
        assert len(alerts) == 1
        assert alerts[0].code == "NEGATIVE_SETTLEMENT"
        assert alerts[0].severity == "warning"
        assert alerts[0].message_id == "pricing.alert.negative_settlement"

    def test_positive_settlement_no_alert(self):
        b = _compute_settlement(
            selling_price=Decimal("70"), shipping=45, commission_pct=Decimal("0")
        )
        assert _generate_alerts(b) == []

    def test_retired_alert_codes_never_appear(self):
        """LOW_MARGIN / SHIPPING_DOMINATES / NEGATIVE_PAYOUT are retired."""
        b = _compute_settlement(
            selling_price=Decimal("70"), shipping=45, commission_pct=Decimal("0")
        )
        codes = {a.code for a in _generate_alerts(b)}
        assert "LOW_MARGIN" not in codes
        assert "SHIPPING_DOMINATES" not in codes
        assert "NEGATIVE_PAYOUT" not in codes


# ─────────────────────────────────────────────────────────────────────────────
# QA Wave 1 — P0.4: unknown leaf raises UnknownCategoryError (→ 422)
# ─────────────────────────────────────────────────────────────────────────────
class TestUnknownLeaf:
    """Regression guard: a leaf_id absent from the pricing lookup must NOT silently
    fall back to a default shipping value — that produces an incorrect settlement.
    The lookup must raise UnknownCategoryError so the router maps it to 422.
    """

    def test_pricing_unknown_leaf_raises(self):
        """A meesho_leaf_id not in the lookup raises UnknownCategoryError.

        Arrange: a leaf id guaranteed not to exist (extremely large integer).
        Act: call get_shipping with that id.
        Assert: UnknownCategoryError is raised (not a silent default).
        """
        from app.modules.pricing.pricing_lookup import UnknownCategoryError, get_shipping

        with pytest.raises(UnknownCategoryError):
            get_shipping("9999999999")  # not in any Meesho category set

    def test_pricing_unknown_leaf_raises_for_commission_too(self):
        """get_commission_default also raises UnknownCategoryError for absent ids."""
        from app.modules.pricing.pricing_lookup import (
            UnknownCategoryError,
            get_commission_default,
        )

        with pytest.raises(UnknownCategoryError):
            get_commission_default("9999999999")
