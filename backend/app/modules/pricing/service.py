"""``pricing`` service layer — settlement calculator + cross-module
orchestration.

Per BACKEND_ARCHITECTURE.md §12.C (LOCKED 2026-06-05) as superseded by the
**W2 Price Calculator rework (census-confirmed settlement model,
2026-06-19)** — authoritative source
``.claude/agent-memory/nexus-level-0-director/project_pricing_transfer_price_model.md``.

Confirmed settlement model (W2)
-------------------------------
The seller enters a **selling price** (the listed Meesho price); the
backend estimates the **bank settlement** Meesho will pay out, using the
per-category constant shipping charge from the static pricing lookup
(``meesho_pricing_lookup.json``, refreshed monthly with the category
scrape).  The model is fully OFFLINE — zero Meesho/supplier calls — and
reproduces Meesho to the paise (verified on 3,772/3,772 categories + the
founder's first real order → ₹61.78).

Formula (each deducted term quantized to 2 dp FIRST, then subtracted)::

    shipping        = pricing_lookup.get_shipping(meesho_leaf_id)
    commission_pct  = request override else 0
    commission_fees = commission_pct × selling_price
    total_price     = selling_price + shipping
    gst_on_shipping = 0.18 × shipping
    tds             = 0.001 × total_price
    tcs             = 0
    estimated_bank_settlement
                    = selling_price − commission_fees − gst_on_shipping − tds − tcs

The seller-side true-profit layer is DEFERRED to V1.5 — this module ships
only the Meesho bank-settlement estimate, not seller profitability.

Public surface
--------------
* :func:`calculate` — main endpoint surface (settlement estimator).
* :func:`apply_price_to_product` — explicit "Use this price" action (W4):
  writes the seller's chosen selling price into the product's
  ``fields_jsonb`` so it flows to the Meesho XLSX export.  NEVER auto-saved
  on :func:`calculate` (founder ruling G-W4-APPLY, Option A — explicit
  action only, never silent mutation).
* :func:`get_last_calc` — cross-module read (dashboard OPTIONAL per §13;
  V1 dashboard does NOT call this).

Cross-module imports (strict allowlist per §3.G + §16)
------------------------------------------------------
This module imports ``from app.modules.catalog import service`` ONLY (the
``assert_product_ownership`` gate, the ``get_product_meesho_leaf_id``
leaf accessor, and — from W4 — the ``patch_product`` write seam used by
:func:`apply_price_to_product` to merge the chosen price into
``fields_jsonb``).  All three are the SAME ``pricing → catalog`` edge in
the §2.D matrix (locked at 1 ✓, line 590) — reusing ``patch_product`` does
NOT add a new matrix cell.  The ``category`` import that #285 retired STAYS
retired — the leaf is reached via catalog, preserving the §2.D matrix.  It
NEVER imports any Meesho/supplier client — the production estimator is pure
arithmetic over a static lookup (HARD RULE).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import service as catalog_service
from app.modules.pricing import pricing_lookup
from app.modules.pricing import repository as pricing_repo
from app.modules.pricing.domain import PricingAlert, PricingCalc, SettlementBreakdown
from app.modules.pricing.exceptions import InvalidPriceInputError
from app.modules.pricing.schemas import (
    PriceCalcAlert,
    PriceCalcRequest,
    PriceCalcResponse,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
_TWO_PLACES = Decimal("0.01")
"""Quantization template — 2 dp, ROUND_HALF_UP (confirmed model, Q4)."""

DEFAULT_COMMISSION_PCT: Decimal = Decimal("0")
"""Census fact: commission is 0% across ALL 3,772 categories.  Kept as a
parameter (not hardcoded into the formula) so a future monthly refresh /
seller override is honored."""

_GST_ON_SHIPPING_RATE: Decimal = Decimal("0.18")
"""18% GST charged on the shipping charge — the seller's actual shipping cost."""

_TDS_RATE: Decimal = Decimal("0.001")
"""0.1% TDS on the total price (selling_price + shipping)."""

_DISCLAIMER: str = (
    "Bank settlement amount may vary slightly based on the quantity in the "
    "order, Meesho commission policy at the time of the order and the actual "
    "weight of the product as calculated by our third party delivery partner."
)
"""Verbatim Meesho disclaimer surfaced near the estimated-settlement output
(model memory 2026-06-19).  Shipped as a literal for V1; an i18n key may be
added later (non-blocking)."""

# ─── W4 "apply chosen price" canonical(s) ────────────────────────────────────
SELLING_PRICE_CANONICAL: str = "meesho_price"
"""The Meesho template canonical that carries the LISTED / SELLING price
(``fetchProductDetailsV3.product_size_data``; W4_EXPORT_SPEC §1.1).  The
export already emits any canonical present in ``products.fields_jsonb`` under
its ``meesho_column_header`` — so writing the seller's chosen selling price
here is the single link that makes the calculator's price reach the XLSX.

OPEN QUESTION (flagged to lead, W4): the schema ALSO carries ``mrp`` (the
strike-through MRP).  The calculator produces ONE seller-chosen number (the
selling price), so :func:`apply_price_to_product` writes ONLY
``meesho_price``.  Whether the "apply" action should ALSO populate ``mrp``
(e.g. default ``mrp = selling_price``, or require a separate MRP input) is a
product decision for the api-routes-builder/FE step — NOT resolved here.  We
do NOT touch ``mrp`` to avoid fabricating a strike-through MRP the seller did
not choose."""


# ─────────────────────────────────────────────────────────────────────────────
# Public — route-internal
# ─────────────────────────────────────────────────────────────────────────────
async def calculate(
    user_id: UUID,
    product_id: UUID,
    request: PriceCalcRequest,
    *,
    db: AsyncSession,
) -> PriceCalcResponse:
    """Main endpoint surface — census-confirmed settlement estimator.

    Steps:
      1. Assert product ownership (cross-module via catalog — M6 gate).
      2. Resolve the category leaf server-side (single source of truth;
         the API does NOT take a category from the client).
      3. Look up the per-category constant shipping charge.
      4. Resolve the commission % (request override, else lookup default = 0).
      5. Compute the settlement breakdown (pure arithmetic, no I/O).
      6. Generate alerts (only NEGATIVE_SETTLEMENT).
      7. Persist to ``pricing_calcs`` (append-only audit row).
      8. Return the wire-shape response.

    Raises:
        ProductNotFoundError: from
            :func:`catalog.service.assert_product_ownership` /
            :func:`catalog.service.get_product_meesho_leaf_id` (404).
        UnknownCategoryError: from :func:`pricing_lookup.get_shipping` when
            the seeded category has no pricing row — NOT caught here; it
            bubbles to the router which maps it to a clean 422.

    A negative ``estimated_bank_settlement`` does NOT raise — it returns 200
    with a single ``NEGATIVE_SETTLEMENT`` alert.
    """
    # Step 1 — cross-module ownership gate (M6).
    await catalog_service.assert_product_ownership(product_id, user_id, db=db)

    # Step 2 — resolve the category leaf server-side (single source of truth).
    meesho_leaf_id = await catalog_service.get_product_meesho_leaf_id(
        product_id, user_id, db=db
    )

    # Step 3 — per-category constant shipping (may raise UnknownCategoryError;
    # let it bubble to the router → 422 pricing.category.no_pricing_data).
    shipping = pricing_lookup.get_shipping(meesho_leaf_id)

    # Step 4 — commission %: request override, else look-through default (0).
    commission_pct = (
        request.commission_pct
        if request.commission_pct is not None
        else pricing_lookup.get_commission_default(meesho_leaf_id)
    )

    # Step 5 — deterministic settlement breakdown.
    breakdown = _compute_settlement(
        selling_price=request.selling_price,
        shipping=shipping,
        commission_pct=commission_pct,
    )

    # Step 6 — alerts (V1 ships exactly one rule).
    alerts = _generate_alerts(breakdown)

    # Step 7 — append-only audit row.
    persisted = await pricing_repo.insert_calc(
        db,
        product_id=product_id,
        selling_price=breakdown.selling_price,
        shipping=breakdown.shipping,
        total_price=breakdown.total_price,
        commission_pct=breakdown.commission_pct,
        commission_fees=breakdown.commission_fees,
        gst_on_shipping=breakdown.gst_on_shipping,
        tds=breakdown.tds,
        tcs=breakdown.tcs,
        estimated_bank_settlement=breakdown.estimated_bank_settlement,
        meesho_leaf_id=meesho_leaf_id,
    )

    logger.info(
        "price-calc product=%s leaf=%s settlement=%s alerts=%d",
        product_id,
        meesho_leaf_id,
        breakdown.estimated_bank_settlement,
        len(alerts),
    )

    # Step 8 — compose wire response.
    return PriceCalcResponse(
        selling_price=breakdown.selling_price,
        shipping=breakdown.shipping,
        total_price=breakdown.total_price,
        commission_pct=breakdown.commission_pct,
        commission_fees=breakdown.commission_fees,
        gst_on_shipping=breakdown.gst_on_shipping,
        tds=breakdown.tds,
        tcs=breakdown.tcs,
        estimated_bank_settlement=breakdown.estimated_bank_settlement,
        disclaimer=_DISCLAIMER,
        alerts=[
            PriceCalcAlert(
                code=a.code,
                message_id=a.message_id,
                severity=a.severity,
            )
            for a in alerts
        ],
        calculated_at=persisted.created_at or datetime.now(timezone.utc),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public — W4 "apply chosen price to product"
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class _PriceFieldsPatch:
    """Minimal duck-typed stand-in for ``catalog.schemas.PatchProductRequest``.

    §16 Contract 4 FORBIDS ``pricing`` importing ``catalog.schemas`` (a
    module's schemas are private wire-shapes).  ``catalog.service.patch_product``
    only reads ``request.fields`` and ``request.status`` — so we hand it a
    local object exposing exactly those two attributes.  This keeps the call on
    the ALLOWED ``pricing → catalog`` service edge (§2.D, line 590) without
    crossing the schema boundary.  ``status`` is always ``None`` — applying a
    price never changes the draft/ready state.
    """

    fields: dict[str, Any] = field(default_factory=dict)
    status: None = None


async def apply_price_to_product(
    user_id: UUID,
    product_id: UUID,
    selling_price: Decimal,
    *,
    db: AsyncSession,
) -> None:
    """Explicit "Use this price" action — write the seller's CHOSEN selling
    price into the product's ``fields_jsonb`` so it flows to the Meesho XLSX
    export (W4_EXPORT_SPEC §2.B; founder ruling G-W4-APPLY Option A).

    The export already emits any canonical present in ``fields_jsonb`` under
    its ``meesho_column_header``; the calculator previously persisted the
    chosen price ONLY to the ``pricing_calcs`` audit table.  This method is
    the single link that lands the price where the export reads it.

    NEVER called from :func:`calculate` — the calculator is an exploration
    tool; the product is mutated ONLY on this explicit seller action (no
    silent auto-save, per the founder sub-ruling).

    Reuse + isolation:
      * Ownership (M6) + per-field schema validation (enum / range — e.g.
        Meesho's ``meesho_price`` min 2 / max 10000) + the atomic JSONB
        ``||`` merge are ALL reused via ``catalog.service.patch_product``
        (the §10.B.2 write seam) — no new write surface, no schema bypass.
        This is the SAME ``pricing → catalog`` §2.D edge as
        ``assert_product_ownership`` (NOT a new matrix cell).
      * The chosen price is written ONLY to
        :data:`SELLING_PRICE_CANONICAL` (``meesho_price``).  ``mrp`` is
        deliberately left untouched (see the constant's OPEN QUESTION note).

    Args:
        user_id: Authenticated principal — tenancy gate.
        product_id: Target product (must be owned, not soft-deleted).
        selling_price: The calculator's chosen selling price (₹, Decimal).

    Raises:
        InvalidPriceInputError: ``selling_price`` is not strictly > 0
            (400 / ``validation.price.invalid_input``).  The route schema
            also enforces this; the service re-checks defensively so the
            invariant holds for any caller.
        ProductNotFoundError: product missing / cross-tenant / soft-deleted,
            from ``catalog.service.patch_product`` → ``assert_product_ownership``
            (404 / ``catalog.product_not_found``).
        ValidationFailedError: the value fails the catalog schema's
            range/enum checks for ``meesho_price`` (422), bubbled verbatim
            from ``patch_product``.

    The commit is owned by the route's ``get_db`` dependency (the merge is
    flushed inside ``patch_product`` but not committed here).
    """
    if selling_price <= 0:
        raise InvalidPriceInputError(
            detail="Selling price must be greater than zero."
        )

    chosen_price = _q(selling_price)

    logger.info(
        "price-apply product=%s canonical=%s value=%s",
        product_id,
        SELLING_PRICE_CANONICAL,
        chosen_price,
    )

    # Single ALLOWED pricing → catalog service edge: ownership + schema
    # validation + atomic JSONB merge, all inside patch_product (is_autosave
    # False → this is an explicit, audited write, not a coalesced draft).
    await catalog_service.patch_product(
        user_id,
        product_id,
        _PriceFieldsPatch(fields={SELLING_PRICE_CANONICAL: chosen_price}),
        is_autosave=False,
        db=db,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public — cross-module surface (§13 OPTIONAL)
# ─────────────────────────────────────────────────────────────────────────────
async def get_last_calc(
    user_id: UUID,
    product_id: UUID,
    *,
    db: AsyncSession,
) -> PricingCalc | None:
    """Return the most recent ``pricing_calcs`` row for ``product_id`` or
    ``None`` if no calc has been run yet.

    Consumed by ``dashboard.service.summary`` per §13 (OPTIONAL).  V1
    dashboard does NOT call this.  Tenancy enforced twice: service-layer
    ownership assert + repository-layer JOIN through ``products``.
    """
    await catalog_service.assert_product_ownership(product_id, user_id, db=db)
    return await pricing_repo.find_latest_by_product(db, user_id, product_id)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers — pure functions, unit-tested in isolation
# ─────────────────────────────────────────────────────────────────────────────
def _compute_settlement(
    *,
    selling_price: Decimal,
    shipping: int,
    commission_pct: Decimal,
) -> SettlementBreakdown:
    """The census-confirmed settlement calculator.

    Deterministic, pure function — NO side effects, NO DB, NO I/O, NO
    Meesho calls.  Each deducted term is quantized to 2 dp via
    ``ROUND_HALF_UP`` FIRST, then subtracted, so the result matches the
    real Meesho payout to the paise.

    Args:
        selling_price: The listed Meesho price (₹, Decimal).
        shipping: Per-category constant shipping charge (₹, integer from
            the lookup).
        commission_pct: Commission percentage actually applied (override or
            the lookup default of 0).

    Returns:
        A :class:`SettlementBreakdown` with all monetary fields at 2 dp.
    """
    selling_price_q = _q(selling_price)
    shipping_q = _q(Decimal(shipping))

    commission_fees = _q(commission_pct * selling_price_q / Decimal("100"))
    total_price = _q(selling_price_q + shipping_q)
    gst_on_shipping = _q(_GST_ON_SHIPPING_RATE * shipping_q)
    tds = _q(_TDS_RATE * total_price)
    tcs = Decimal("0.00")

    estimated_bank_settlement = _q(
        selling_price_q - commission_fees - gst_on_shipping - tds - tcs
    )

    return SettlementBreakdown(
        selling_price=selling_price_q,
        shipping=shipping_q,
        total_price=total_price,
        commission_pct=_q(commission_pct),
        commission_fees=commission_fees,
        gst_on_shipping=gst_on_shipping,
        tds=tds,
        tcs=tcs,
        estimated_bank_settlement=estimated_bank_settlement,
    )


def _generate_alerts(breakdown: SettlementBreakdown) -> list[PricingAlert]:
    """Apply the single locked alert rule to the breakdown.

    Pure function — no side effects, no I/O.  V1 ships exactly one alert:
    ``NEGATIVE_SETTLEMENT`` when the estimated bank settlement is strictly
    below zero.
    """
    alerts: list[PricingAlert] = []

    if breakdown.estimated_bank_settlement < Decimal("0"):
        alerts.append(
            PricingAlert(
                code="NEGATIVE_SETTLEMENT",
                message_id="pricing.alert.negative_settlement",
                severity="warning",
            )
        )

    return alerts


def _q(value: Decimal) -> Decimal:
    """Quantize a Decimal to 2 dp with ``ROUND_HALF_UP`` (confirmed model,
    Q4).  Centralised so every monetary surface rounds identically."""
    return value.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


__all__ = [
    "calculate",
    "apply_price_to_product",
    "get_last_calc",
    "SELLING_PRICE_CANONICAL",
    # Pure-function exports for unit-tests (NOT part of the cross-module
    # surface — §16 callers must use ``calculate`` / ``apply_price_to_product``
    # / ``get_last_calc``).
    "_compute_settlement",
    "_generate_alerts",
    "DEFAULT_COMMISSION_PCT",
]
