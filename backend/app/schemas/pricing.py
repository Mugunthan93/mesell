"""PriceIntel request/response schemas."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AlertSeverity = Literal["info", "warn", "critical"]


class PricingRequest(BaseModel):
    selling_price: Decimal = Field(..., gt=0)
    cost_price: Decimal = Field(..., gt=0)
    weight_grams: int = Field(..., ge=1)
    category: str | None = None
    return_rate: float | None = Field(default=None, ge=0, le=1)
    ad_spend: Decimal = Field(default=Decimal("0"), ge=0)
    packaging: Decimal = Field(default=Decimal("12"), ge=0)
    zone: Literal["local", "regional", "national", "special"] | None = None


class PricingAlert(BaseModel):
    code: str
    severity: AlertSeverity
    message: str


class PricingResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    selling_price: Decimal
    cost_price: Decimal
    weight_grams: int
    category: str | None = None
    zone: str
    shipping_slab: dict
    shipping_cost: Decimal
    shipping_gst: Decimal
    payment_processing: Decimal
    return_provision: Decimal
    packaging: Decimal
    ad_spend: Decimal
    commission: Decimal
    total_costs: Decimal
    net_profit: Decimal
    margin_percent: Decimal
    return_rate_used: float
    alerts: list[PricingAlert] = []
    authenticated: bool = False
