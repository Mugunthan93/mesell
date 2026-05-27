"""Pricing engine unit tests + public endpoint."""

from decimal import Decimal

import pytest

from app.services.pricing_engine import calculate_pnl


def test_pnl_matches_manual_spreadsheet():
    p = calculate_pnl(
        selling_price=Decimal("599"),
        cost_price=Decimal("250"),
        weight_grams=480,
        category="Kurtis",
    )
    assert p["shipping_cost"] == Decimal("65.00")  # <=500g national slab
    assert p["shipping_gst"] == Decimal("11.70")
    assert p["payment_processing"] == Decimal("11.98")
    assert p["return_provision"] == Decimal("149.75")  # 599 * 25%
    assert p["total_costs"] == Decimal("500.43")
    assert p["net_profit"] == Decimal("98.57")
    assert p["margin_percent"] == Decimal("16.46")


def test_weight_slab_warning_fires():
    p = calculate_pnl(
        selling_price=Decimal("799"),
        cost_price=Decimal("300"),
        weight_grams=480,  # within 150g of 500g cutoff
        category="Kurtis",
    )
    codes = [a.code for a in p["alerts"]]
    assert "weight_slab_warning" in codes


def test_low_margin_alert():
    p = calculate_pnl(
        selling_price=Decimal("300"),
        cost_price=Decimal("220"),
        weight_grams=400,
        category="Kurtis",
    )
    codes = [a.code for a in p["alerts"]]
    assert "low_margin" in codes


def test_slab_selection_above_largest_adds_surcharge():
    p = calculate_pnl(
        selling_price=Decimal("3000"),
        cost_price=Decimal("1500"),
        weight_grams=22000,  # exceeds 20kg slab
        category="Bedsheets",
    )
    # Surcharge applies: 4 extra 500g units beyond 20000g.
    assert p["shipping_cost"] > Decimal("520")


@pytest.mark.asyncio
async def test_pricing_endpoint_public(client):
    resp = await client.post(
        "/api/v1/pricing/calculate",
        json={"selling_price": 599, "cost_price": 250, "weight_grams": 480, "category": "Kurtis"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["authenticated"] is False
    assert body["net_profit"] is not None


@pytest.mark.asyncio
async def test_pricing_endpoint_authenticated(client):
    await client.post("/api/v1/auth/send-otp", json={"phone": "+919555555555"})
    auth = await client.post("/api/v1/auth/verify-otp", json={"phone": "+919555555555", "otp": "1234"})
    token = auth.json()["token"]
    resp = await client.post(
        "/api/v1/pricing/calculate",
        headers={"Authorization": f"Bearer {token}"},
        json={"selling_price": 599, "cost_price": 250, "weight_grams": 480, "category": "Kurtis"},
    )
    assert resp.status_code == 200
    assert resp.json()["authenticated"] is True
