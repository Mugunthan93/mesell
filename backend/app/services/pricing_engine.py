"""Meesho P&L calculator.

Cost components (per unit):
    shipping  — looked up from ``meesho_shipping_slabs.json`` by weight + zone
    shipping_gst — 18% of shipping (Meesho charges this back)
    payment_processing — 2% of selling_price
    return_provision — selling_price × expected_return_rate
    packaging — flat per-unit packaging cost (default ₹12)
    ad_spend  — caller-provided
    commission — 0% on Meesho today (kept for future)

Alerts:
    weight_slab_warning — within 150g of the next slab (saves ₹15-50/order)
    low_margin — margin below 15%
    competitor_context — placeholder, requires marketplace data we don't have yet
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.data import get_category_config, load_shipping_slabs
from app.schemas.pricing import PricingAlert

_TWOPL = Decimal("0.01")
_HUNDRED = Decimal("100")
SLAB_WARN_BUFFER_GRAMS = 150
LOW_MARGIN_THRESHOLD = Decimal("15")


def _q(x: Decimal | int | float) -> Decimal:
    return Decimal(str(x)).quantize(_TWOPL, rounding=ROUND_HALF_UP)


def _pick_slab(weight_grams: int, slabs: list[dict]) -> dict:
    for slab in slabs:
        if weight_grams <= slab["max_grams"]:
            return slab
    return slabs[-1]


def calculate_pnl(
    *,
    selling_price: Decimal,
    cost_price: Decimal,
    weight_grams: int,
    category: str | None = None,
    return_rate: float | None = None,
    ad_spend: Decimal = Decimal("0"),
    packaging: Decimal = Decimal("12"),
    zone: str | None = None,
) -> dict:
    shipping_cfg = load_shipping_slabs()
    zone = zone or shipping_cfg.get("default_zone", "national")
    slab = _pick_slab(weight_grams, shipping_cfg["slabs"])
    shipping = Decimal(str(slab[zone]))
    # If weight exceeds the largest slab, add per-500g surcharges.
    largest = shipping_cfg["slabs"][-1]
    if weight_grams > largest["max_grams"]:
        extra_units = -(-(weight_grams - largest["max_grams"]) // 500)  # ceil
        shipping += Decimal(str(shipping_cfg["additional_500g_rate"][zone])) * extra_units

    shipping_gst = (shipping * Decimal(str(shipping_cfg["gst_on_shipping_percent"])) / _HUNDRED)
    payment_pp = (
        selling_price * Decimal(str(shipping_cfg["payment_processing_percent"])) / _HUNDRED
    )

    cfg = get_category_config(category or "_default")
    rr = return_rate if return_rate is not None else cfg.get("default_return_rate", 0.22)
    return_provision = selling_price * Decimal(str(rr))

    commission = Decimal("0")  # Meesho: 0% commission.

    total_costs = (
        cost_price
        + shipping
        + shipping_gst
        + payment_pp
        + return_provision
        + packaging
        + ad_spend
        + commission
    )
    net_profit = selling_price - total_costs
    margin_percent = (net_profit / selling_price * _HUNDRED) if selling_price else Decimal("0")

    alerts: list[PricingAlert] = []
    if slab is not largest and weight_grams >= slab["max_grams"] - SLAB_WARN_BUFFER_GRAMS:
        next_slab = shipping_cfg["slabs"][shipping_cfg["slabs"].index(slab) + 1]
        gap = slab["max_grams"] - weight_grams
        delta = Decimal(str(next_slab[zone])) - shipping
        alerts.append(
            PricingAlert(
                code="weight_slab_warning",
                severity="warn",
                message=(
                    f"You're {gap}g under the {slab['max_grams']}g slab. Dropping below "
                    f"{slab['max_grams']}g saves ~₹{_q(delta)} per order in shipping."
                ),
            )
        )

    if margin_percent < LOW_MARGIN_THRESHOLD:
        alerts.append(
            PricingAlert(
                code="low_margin",
                severity="critical" if margin_percent < 5 else "warn",
                message=f"Margin is only {_q(margin_percent)}%. Increase selling price or reduce cost/return rate.",
            )
        )

    return {
        "selling_price": _q(selling_price),
        "cost_price": _q(cost_price),
        "weight_grams": weight_grams,
        "category": category,
        "zone": zone,
        "shipping_slab": slab,
        "shipping_cost": _q(shipping),
        "shipping_gst": _q(shipping_gst),
        "payment_processing": _q(payment_pp),
        "return_provision": _q(return_provision),
        "packaging": _q(packaging),
        "ad_spend": _q(ad_spend),
        "commission": _q(commission),
        "total_costs": _q(total_costs),
        "net_profit": _q(net_profit),
        "margin_percent": _q(margin_percent),
        "return_rate_used": float(rr),
        "alerts": alerts,
    }
