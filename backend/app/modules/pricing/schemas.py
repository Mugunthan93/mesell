"""``pricing`` Pydantic v2 wire-shape models — request + response surfaces.

Per BACKEND_ARCHITECTURE.md §12.E (LOCKED 2026-06-05) as superseded by the
**W2 Price Calculator rework (census-confirmed settlement model, 2026-06-19)** —
authoritative source
``.claude/agent-memory/nexus-level-0-director/project_pricing_transfer_price_model.md``.

Census-confirmed settlement model (W2)
--------------------------------------
The calculator runs FORWARD: the seller enters a **selling price** (the listed
Meesho price) and the backend estimates the **bank settlement** Meesho will pay
out.  Profit / margin / input cost are DEFERRED to V1.5
(``G-NETPROFIT`` gate) — no such fields exist anywhere in request/response/domain.

* :class:`PriceCalcRequest` — ``selling_price`` is the primary input;
  ``commission_pct`` is an optional seller override (default resolved server-side
  from the lookup = 0).
* :class:`PriceCalcAlert` — V1 ships exactly ONE code: ``NEGATIVE_SETTLEMENT``.
* :class:`PriceCalcResponse` — the complete bank-settlement breakdown.

Breaking change from #285 (W3 note)
------------------------------------
The request field ``meesho_price`` has been renamed to ``selling_price`` and all
other #285 request fields (``input_cost``, ``return_rate_pct``, ``mrp``,
``override_*``) are REMOVED.  ``extra="forbid"`` means a stale FE sending the
old fields gets a 422.  W3 frontend ships the new body in lockstep (see W3
hand-off memo).

All monetary values are :class:`~decimal.Decimal` with 2 dp — never
:class:`float` per CLAUDE.md "Coding Conventions" + §4.D numeric precision rule.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# Request  (§12.M + W2 confirmed model)
# ─────────────────────────────────────────────────────────────────────────────
class PriceCalcRequest(BaseModel):
    """Body for ``POST /api/v1/products/{id}/price-calc``.

    Minimal contract — the API does NOT take a category identifier.  The
    product already carries ``category_id`` and the service resolves the
    Meesho leaf id server-side (single source of truth, avoids client/category
    drift bug per W2_BACKEND_SPEC §2.1 decision).

    A negative ``estimated_bank_settlement`` returns 200 with a
    ``NEGATIVE_SETTLEMENT`` alert — never a 400.

    ``extra="forbid"`` is intentional: a stale frontend sending the old #285
    fields (``meesho_price``, ``input_cost``, etc.) will receive a clean 422
    rather than silently ignoring the extra data.
    """

    model_config = ConfigDict(extra="forbid")

    selling_price: Decimal = Field(
        gt=0,
        decimal_places=2,
        description=(
            "Listed / selling price on Meesho, in INR — drives the settlement "
            "estimate.  Renamed from #285 ``meesho_price``."
        ),
    )
    commission_pct: Decimal | None = Field(
        default=None,
        ge=0,
        le=Decimal("100"),
        decimal_places=2,
        description=(
            "Optional seller commission % override (0–100).  When omitted the "
            "service resolves the lookup default (0 across all 3,772 categories "
            "per census).  Kept as a parameter so a future monthly refresh or "
            "per-seller negotiated rate is honored."
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Alert  (V1 ships ONE code)
# ─────────────────────────────────────────────────────────────────────────────
class PriceCalcAlert(BaseModel):
    """Wire-shape pricing alert.

    V1 ships exactly one alert code (``NEGATIVE_SETTLEMENT``).  The service
    maps :class:`~app.modules.pricing.domain.PricingAlert` → this model.
    """

    code: Literal["NEGATIVE_SETTLEMENT"]
    message_id: str = Field(
        description=(
            "i18n lookup key per §5A.H — resolved client-side.  "
            "V1 value: ``pricing.alert.negative_settlement``."
        ),
    )
    severity: Literal["warning"]


# ─────────────────────────────────────────────────────────────────────────────
# Response  (W3/W4 bind to this contract — DO NOT change without coordinator)
# ─────────────────────────────────────────────────────────────────────────────
_DISCLAIMER: str = (
    "Bank settlement amount may vary slightly based on the quantity in the "
    "order, Meesho commission policy at the time of the order and the actual "
    "weight of the product as calculated by our third party delivery partner."
)
"""Verbatim Meesho disclaimer.  Shipped as a literal for V1; an i18n key
(``pricing.disclaimer``) may be added later — non-blocking per W2 spec."""


class PriceCalcResponse(BaseModel):
    """200-OK body for ``POST /api/v1/products/{id}/price-calc``.

    All monetary values in INR with exactly 2 decimal places (Decimal,
    serialized as strings to preserve precision — the frontend parses via
    ``Number()``).

    Field set is the W3/W4 contract.  Do NOT add or rename fields without
    backend-coordinator approval + W3 FE lock-step.
    """

    # ── Echo of request (for display / debugging) ─────────────────────────
    selling_price: Decimal
    """The listed Meesho price echoed from the request (₹, 2 dp)."""

    # ── Settlement breakdown ──────────────────────────────────────────────
    shipping: Decimal
    """Per-category constant shipping charge from the lookup (₹, 2 dp)."""

    total_price: Decimal
    """selling_price + shipping (₹, 2 dp)."""

    commission_pct: Decimal
    """Commission % actually applied — the override or the lookup default (0)."""

    commission_fees: Decimal
    """commission_pct × selling_price (₹, 2 dp)."""

    gst_on_shipping: Decimal
    """18% × shipping — the seller's real shipping cost (₹, 2 dp)."""

    tds: Decimal
    """0.1% × total_price — TDS deduction (₹, 2 dp)."""

    tcs: Decimal
    """Tax collected at source — always 0.00 per census (₹, 2 dp)."""

    # ── Headline output ───────────────────────────────────────────────────
    estimated_bank_settlement: Decimal
    """selling_price − commission_fees − gst_on_shipping − tds − tcs (₹, 2 dp).
    May be negative (→ NEGATIVE_SETTLEMENT alert).  Never a 400."""

    # ── Metadata ─────────────────────────────────────────────────────────
    disclaimer: str = Field(default=_DISCLAIMER)
    """Verbatim Meesho disclaimer (the model memory text, 2026-06-19)."""

    alerts: list[PriceCalcAlert]
    """0 or 1 alerts (V1 ships only NEGATIVE_SETTLEMENT)."""

    calculated_at: datetime
    """UTC timestamp of the persisted ``pricing_calcs`` row."""


__all__ = [
    "PriceCalcRequest",
    "PriceCalcAlert",
    "PriceCalcResponse",
]
