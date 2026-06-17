"""``pricing`` Pydantic v2 wire-shape models — request + response surfaces.

Per BACKEND_ARCHITECTURE.md §12.E (LOCKED 2026-06-05).

Copied verbatim from the monolith ``app/modules/pricing/schemas.py`` under the
§16.G discipline (zero drift — THE FROZEN CONTRACT per spec §1).

THE FROZEN DECIMAL-STRING CONTRACT (spec §1 — zero drift)
---------------------------------------------------------
9 of 11 :class:`PriceCalcResponse` fields are bare :class:`~decimal.Decimal`:
``mrp``, ``meesho_price``, ``seller_price``, ``commission_pct``,
``commission_amount``, ``gst_pct``, ``gst_amount``, ``profit``, ``profit_pct``.
Pydantic v2 emits bare ``Decimal`` as JSON **strings** (e.g. ``"mrp":"157.96"``).
There are NO ``json_encoders``, NO ``model_config`` serialization overrides, and
NO float replacements anywhere in this file — preserving the string emission
exactly.  The frontend (future wiring) expects JSON strings for these fields.

V1.5 forward-compatibility
--------------------------
:class:`PriceCalcRequest` carries ``override_commission_pct`` and
``override_gst_pct`` as optional fields per §12.E.  V1 IGNORES them; V1.5
Pro-tier may honor them per §12.K extraction notes.  The fields ship in V1 so
the request shape does not break when V1.5 widens behavior.

All monetary values are :class:`~decimal.Decimal` with 2 dp — never
:class:`float` per CLAUDE.md "Coding Conventions" + §4.D numeric precision
rule.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# Request
# ─────────────────────────────────────────────────────────────────────────────
class PriceCalcRequest(BaseModel):
    """Body for ``POST /api/v1/products/{id}/price-calc``.

    Per §12.B.1 + §12.E.  Pydantic validates the field constraints at the
    route boundary; service-layer business-rule checks (V1.5) are
    surfaced via :class:`~app.exceptions.InvalidPriceInputError`.
    """

    model_config = ConfigDict(extra="forbid")

    input_cost: Decimal = Field(
        gt=0,
        decimal_places=2,
        description="Cost of goods per unit, in INR.",
    )
    target_margin_pct: Decimal = Field(
        default=Decimal("30"),
        ge=0,
        le=Decimal("500"),
        decimal_places=2,
        description="Desired profit margin as a percentage of input_cost.",
    )
    override_commission_pct: Decimal | None = Field(
        default=None,
        ge=0,
        le=Decimal("100"),
        decimal_places=2,
        description="V1.5+ Pro override; V1 ignores this field.",
    )
    override_gst_pct: Decimal | None = Field(
        default=None,
        ge=0,
        le=Decimal("100"),
        decimal_places=2,
        description="V1.5+ Pro override; V1 ignores this field.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Alert (wire shape)
# ─────────────────────────────────────────────────────────────────────────────
class PriceCalcAlert(BaseModel):
    """Wire-shape pricing alert.  See :class:`~app.domain.PricingAlert`
    for the internal dataclass that the service constructs and the router
    maps to this Pydantic model."""

    code: Literal["LOW_MARGIN", "HIGH_MRP_MULTIPLIER", "THIN_PROFIT"]
    message_id: str = Field(
        description="validation_message_id per §5A.H — resolved client-side via i18n.",
    )
    severity: Literal["warning", "info"]


# ─────────────────────────────────────────────────────────────────────────────
# Response
# ─────────────────────────────────────────────────────────────────────────────
class PriceCalcResponse(BaseModel):
    """200-OK body for ``POST /api/v1/products/{id}/price-calc``.

    All monetary values in INR with 2 decimal places (quantized
    ``ROUND_HALF_EVEN`` per the §12.B.1 step 6 lock).

    THE FROZEN CONTRACT: bare Decimal fields emit as JSON strings — NO float,
    NO json_encoders, NO model_config serialization override (spec §1).
    """

    mrp: Decimal
    meesho_price: Decimal
    seller_price: Decimal
    commission_pct: Decimal
    commission_amount: Decimal
    gst_pct: Decimal
    gst_amount: Decimal
    profit: Decimal
    profit_pct: Decimal
    alerts: list[PriceCalcAlert]
    calculated_at: datetime


__all__ = [
    "PriceCalcRequest",
    "PriceCalcAlert",
    "PriceCalcResponse",
]
