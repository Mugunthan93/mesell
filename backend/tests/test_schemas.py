"""Pydantic schema validators."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.auth import SendOTPRequest, UserResponse, VerifyOTPRequest
from app.schemas.catalog import CatalogCreate, CatalogUpdate
from app.schemas.pricing import PricingRequest
from app.schemas.sku import SKUCreate


# ---- auth -----------------------------------------------------------------

@pytest.mark.parametrize(
    "phone",
    ["+919876543210", "+916123456789", "+918888777766"],
)
def test_phone_valid(phone):
    assert SendOTPRequest(phone=phone).phone == phone


@pytest.mark.parametrize(
    "phone",
    [
        "9876543210",        # no +91
        "+91987654321",      # too short
        "+9198765432101",    # too long
        "+919876543abc",     # not digits
        "+925876543210",     # not India (Pakistan)
        "+9151234567890",    # 10-digit number doesn't start 6-9
        "919876543210",      # missing leading +
        " +919876543210",    # accepted after strip — covered below separately
    ],
)
def test_phone_invalid(phone):
    if phone == " +919876543210":
        # Whitespace gets stripped, so this one is actually valid.
        assert SendOTPRequest(phone=phone).phone == "+919876543210"
        return
    with pytest.raises(ValidationError):
        SendOTPRequest(phone=phone)


def test_verify_otp_length_constraints():
    VerifyOTPRequest(phone="+919876543210", otp="1234")  # ok
    VerifyOTPRequest(phone="+919876543210", otp="123456")  # ok
    with pytest.raises(ValidationError):
        VerifyOTPRequest(phone="+919876543210", otp="12")
    with pytest.raises(ValidationError):
        VerifyOTPRequest(phone="+919876543210", otp="1234567")


def test_user_response_from_attributes():
    """Sanity-check from_attributes works with a duck-typed object."""
    class M:
        id = "00000000-0000-0000-0000-000000000001"
        phone = "+919876543210"
        name = None
        plan = "free"
        catalogs_used = 0
        catalogs_limit = 5

    u = UserResponse.model_validate(M())
    assert u.plan == "free"


# ---- catalog --------------------------------------------------------------

def test_catalog_create_requires_name():
    with pytest.raises(ValidationError):
        CatalogCreate(name="")


def test_catalog_update_accepts_partial():
    # Partial updates should not require every field.
    upd = CatalogUpdate(name="Renamed")
    assert upd.name == "Renamed"
    assert upd.category is None


def test_catalog_update_rejects_unknown_status():
    with pytest.raises(ValidationError):
        CatalogUpdate(status="nonsense")  # type: ignore[arg-type]


# ---- sku ------------------------------------------------------------------

def test_sku_create_minimal():
    sku = SKUCreate(product_name="Saree")
    assert sku.product_name == "Saree"
    assert sku.sort_order == 0


def test_sku_create_with_prices():
    sku = SKUCreate(product_name="Saree", cost_price=Decimal("250.50"), selling_price=Decimal("599"))
    assert sku.cost_price == Decimal("250.50")


# ---- pricing --------------------------------------------------------------

def test_pricing_request_requires_positive_price():
    with pytest.raises(ValidationError):
        PricingRequest(selling_price=0, cost_price=10, weight_grams=100)
    with pytest.raises(ValidationError):
        PricingRequest(selling_price=10, cost_price=-1, weight_grams=100)


def test_pricing_request_return_rate_bounds():
    PricingRequest(selling_price=1, cost_price=1, weight_grams=1, return_rate=0)
    PricingRequest(selling_price=1, cost_price=1, weight_grams=1, return_rate=1)
    with pytest.raises(ValidationError):
        PricingRequest(selling_price=1, cost_price=1, weight_grams=1, return_rate=1.01)


def test_pricing_request_weight_must_be_positive():
    with pytest.raises(ValidationError):
        PricingRequest(selling_price=1, cost_price=1, weight_grams=0)
