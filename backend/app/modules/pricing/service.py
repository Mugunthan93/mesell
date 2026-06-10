"""``pricing`` service layer — P&L calculator + cross-module orchestration.

Per BACKEND_ARCHITECTURE.md §12.C (LOCKED 2026-06-05).

Public surface
--------------

Route-internal (driven by §12.B.1):

* :func:`calculate` — main endpoint surface; locked flow per §12.B.1
  steps 2-9.

Cross-module surfaces (consumed via ``from app.modules.pricing import
service as pricing_service``):

* :func:`get_last_calc` — consumed by ``dashboard.service.summary``
  (§13 OPTIONAL — same posture as ``image.service.summary`` per §11.C).
  V1 dashboard does NOT call this per the §2.D matrix lock at 8 ✓.

Cross-module imports (strict allowlist per §3.G + §16)
------------------------------------------------------
This module imports ``from app.modules.catalog import service`` and
``from app.modules.category import service`` ONLY.  It NEVER imports
``app.modules.catalog.repository`` or ``app.modules.category.repository``.
It NEVER imports ``app.adapters.gemini`` — pricing is deterministic math
per §6A + §12.H (no AI in V1).

DECISION FLAGS
--------------
§12-PRICING-D1 — :func:`category.service.get_commission` returns
    ``Decimal("0.00")`` (not ``None``) when commission is unseeded; this
    service treats the zero return as the missing-signal and raises
    :class:`CommissionMissingError`.  See exceptions module docstring.

§12-PRICING-D2 — The §12.J test #3 golden ``mrp ≈ 151.52`` is
    inconsistent with the §12.B.1 step 6 locked formula.  The formula
    (back-solve from ``seller_price = mrp − commission − GST-on-commission``)
    yields ``mrp = 130 / (1 − 0.15 − 0.18 × 0.15) = 130 / 0.823 ≈ 157.96``
    for the fixture ``(input_cost=100, target_margin_pct=30,
    commission_pct=15, gst_pct=18)``.  Follow the locked formula; the
    unit test asserts ``Decimal("157.96")``.

§12-PRICING-D3 — 3 exception classes per §12.G (PricingError +
    InvalidPriceInputError + CommissionMissingError).  Master prompt's
    "5 classes" tally counted the 5 i18n keys (which include 3 alert
    codes; alerts are NOT exceptions per §12.F).

§12-PRICING-D4 — ``pricing_calcs`` DDL (Wave 1 LOCKED) has structured
    columns (mrp / meesho_price / seller_price / commission_pct /
    gst_pct / margin / margin_pct / created_at) — NOT
    ``{user_id, input_jsonb, output_jsonb, calculated_at}`` per §12.B.1
    step 8.  Persistence uses structured columns; tenancy is via
    product → user FK chain + service-layer ownership gate.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import ROUND_HALF_EVEN, Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import service as catalog_service
from app.modules.category import service as category_service
from app.modules.pricing import repository as pricing_repo
from app.modules.pricing.domain import PnLBreakdown, PricingAlert, PricingCalc
from app.modules.pricing.exceptions import CommissionMissingError
from app.modules.pricing.schemas import (
    PriceCalcAlert,
    PriceCalcRequest,
    PriceCalcResponse,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Constants (§12.B.1 step 6 + §12.F)
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_GST_PCT: Decimal = Decimal("18")
"""V1 default GST rate.  V1.5 may make this per-category via the
``override_gst_pct`` Pro-tier request field per §12.E."""

_TWO_PLACES = Decimal("0.01")
"""Quantization template — 2 decimal places, banker's rounding
(``ROUND_HALF_EVEN``) per the §12.B.1 step 6 lock + CLAUDE.md numeric
precision rule."""

_HUNDRED = Decimal("100")

# Alert thresholds (§12.F + §12.J test #4).
_LOW_MARGIN_THRESHOLD_PCT: Decimal = Decimal("10")
"""``profit_pct < 10`` → ``LOW_MARGIN``."""

_HIGH_MRP_MULTIPLIER: Decimal = Decimal("3")
"""``mrp / input_cost > 3`` → ``HIGH_MRP_MULTIPLIER``."""

_THIN_PROFIT_THRESHOLD: Decimal = Decimal("50")
"""``profit < 50`` (INR) → ``THIN_PROFIT``."""


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
    """Main endpoint surface — locked flow per §12.B.1 steps 2-9.

    Steps:
      2. Assert product ownership (cross-module via catalog).
      3. Load the product to obtain ``category_id``.
      4. Fetch commission for that category (cross-module via category).
      5. If commission resolves to zero → raise
         :class:`CommissionMissingError` (D1).
      6. Compute the P&L breakdown deterministically (no I/O).
      7. Generate alerts from the breakdown.
      8. Persist to ``pricing_calcs`` (append-only audit row per D4).
      9. Return the wire-shape response.

    Raises:
        ProductNotFoundError: from
            :func:`catalog.service.assert_product_ownership` (404).
        CommissionMissingError: when the category has no usable
            commission (422).
    """
    # Step 2 — cross-module ownership gate (M6).
    await catalog_service.assert_product_ownership(product_id, user_id, db=db)

    # Step 3 — load product to obtain category_id (single-row read).
    # We re-use the catalog repository surface indirectly: the call
    # above already validated ownership; we now need the category_id.
    # Per §16 + §3.G we MUST NOT touch catalog.repository directly.  The
    # cleanest cross-module read for category_id is to call
    # `get_product_for_export` (overkill — it builds a full snapshot)
    # OR to call a leaner helper.  Catalog does not expose a bare
    # `get_category_id(product_id)` surface in V1; the bare ORM query
    # would require importing catalog.repository which violates §16.
    #
    # Resolution: read the product row via ``db.get`` on the shared ORM
    # model — this is a read of the *shared* ORM, not a cross-module
    # repository call, and the §16 invariant explicitly permits shared
    # model use across modules (the violation is calling another
    # module's *repository*).  Tenancy is already established by step 2.
    from app.shared.models.product import Product as ProductORM  # noqa: PLC0415

    product = await db.get(ProductORM, product_id)
    if product is None or product.deleted_at is not None:
        # Defensive — step 2 already validated; this catches a TOCTOU
        # race where the product was soft-deleted between the gate and
        # the read.  Surface as a clean ProductNotFoundError via the
        # catalog exception so the envelope is identical.
        from app.modules.catalog.exceptions import ProductNotFoundError  # noqa: PLC0415
        raise ProductNotFoundError()

    category_id = product.category_id

    # Step 4 — fetch commission (cross-module via category service).
    commission_pct = await category_service.get_commission(category_id, db=db)

    # Step 5 — D1: §9 returns Decimal("0.00") for the missing case.
    if commission_pct == Decimal("0.00"):
        raise CommissionMissingError()

    # Step 6 — deterministic P&L (V1 ignores override_* fields per §12.E).
    breakdown = _compute_pnl(
        input_cost=request.input_cost,
        target_margin_pct=request.target_margin_pct,
        commission_pct=commission_pct,
        gst_pct=DEFAULT_GST_PCT,
    )

    # Step 7 — alerts from the deterministic breakdown.
    alerts = _generate_alerts(breakdown, input_cost=request.input_cost)

    # Step 8 — append-only audit row.
    persisted = await pricing_repo.insert_calc(
        db,
        product_id=product_id,
        mrp=breakdown.mrp,
        meesho_price=breakdown.meesho_price,
        seller_price=breakdown.seller_price,
        commission_pct=breakdown.commission_pct,
        gst_pct=breakdown.gst_pct,
        margin=breakdown.profit,
        margin_pct=breakdown.profit_pct,
    )

    # Step 9 — compose wire response.
    return PriceCalcResponse(
        mrp=breakdown.mrp,
        meesho_price=breakdown.meesho_price,
        seller_price=breakdown.seller_price,
        commission_pct=breakdown.commission_pct,
        commission_amount=breakdown.commission_amount,
        gst_pct=breakdown.gst_pct,
        gst_amount=breakdown.gst_amount,
        profit=breakdown.profit,
        profit_pct=breakdown.profit_pct,
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

    Consumed by ``dashboard.service.summary`` per §13 (OPTIONAL — same
    posture as ``image.service.summary`` per §11.C).  V1 dashboard does
    NOT call this (the §2.D matrix is kept at 8 ✓ per the founder
    ruling — see §13.K).  V1.5 dashboard amendment may opt in for
    "low margin" badges per §13 prose.

    Tenancy is enforced twice:
      1. Service layer — assert product ownership upstream.
      2. Repository layer — JOIN through ``products`` with
         ``Product.user_id == user_id`` per §12-PRICING-D4.
    """
    await catalog_service.assert_product_ownership(product_id, user_id, db=db)
    return await pricing_repo.find_latest_by_product(db, user_id, product_id)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers — pure functions, unit-tested in isolation
# ─────────────────────────────────────────────────────────────────────────────
def _compute_pnl(
    *,
    input_cost: Decimal,
    target_margin_pct: Decimal,
    commission_pct: Decimal,
    gst_pct: Decimal,
) -> PnLBreakdown:
    """The locked P&L algorithm per §12.B.1 step 6.

    Deterministic, pure function, NO side effects, NO DB, NO I/O.  All
    monetary values quantize to 2 dp via banker's rounding
    (``ROUND_HALF_EVEN``).

    Formula:

    * ``seller_price = input_cost × (1 + target_margin_pct/100)``
    * ``mrp = seller_price / (1 − commission_pct/100 − (gst_pct/100) × (commission_pct/100))``
    * ``commission_amount = mrp × commission_pct / 100``
    * ``gst_amount = commission_amount × gst_pct / 100``  (GST charged
      on commission, not on full MRP — Meesho's seller-fee structure)
    * ``meesho_price = mrp`` (V1; V1.5 may differentiate)
    * ``profit = seller_price − input_cost``
    * ``profit_pct = profit / input_cost × 100``

    Per §12-PRICING-D2: the golden value in §12.J test #3 prose is
    inconsistent with this formula; the formula is the lock.
    """
    seller_price = _q(input_cost * (Decimal("1") + target_margin_pct / _HUNDRED))

    denom = Decimal("1") - commission_pct / _HUNDRED - (
        gst_pct / _HUNDRED
    ) * (commission_pct / _HUNDRED)
    # Defensive: in V1 denom is always > 0 because commission_pct ∈ [0, 100]
    # and gst_pct = 18 keep the denominator positive.  The guard is here
    # so a future V1.5 override surface that allows high commission +
    # high GST cannot silently divide by zero.
    if denom <= Decimal("0"):
        # Surface a clear error rather than ZeroDivisionError or a
        # nonsensical negative MRP.  This is reachable only via the
        # V1.5 override fields when used with extreme combinations.
        from app.modules.pricing.exceptions import InvalidPriceInputError  # noqa: PLC0415
        raise InvalidPriceInputError(
            "Commission + GST combine to a non-positive denominator; "
            "the resulting MRP would be undefined or negative.",
        )

    mrp = _q(seller_price / denom)
    commission_amount = _q(mrp * commission_pct / _HUNDRED)
    gst_amount = _q(commission_amount * gst_pct / _HUNDRED)
    meesho_price = mrp
    profit = _q(seller_price - input_cost)
    profit_pct = _q(profit / input_cost * _HUNDRED)

    return PnLBreakdown(
        mrp=mrp,
        meesho_price=meesho_price,
        seller_price=seller_price,
        commission_pct=_q(commission_pct),
        commission_amount=commission_amount,
        gst_pct=_q(gst_pct),
        gst_amount=gst_amount,
        profit=profit,
        profit_pct=profit_pct,
    )


def _generate_alerts(
    breakdown: PnLBreakdown,
    *,
    input_cost: Decimal,
) -> list[PricingAlert]:
    """Apply the 3 locked alert rules per §12.F to the breakdown.

    Pure function — no side effects, no I/O.  Multiple alerts may fire
    simultaneously (per §12.F).
    """
    alerts: list[PricingAlert] = []

    # Rule 1 — LOW_MARGIN: profit_pct strictly less than 10.
    if breakdown.profit_pct < _LOW_MARGIN_THRESHOLD_PCT:
        alerts.append(
            PricingAlert(
                code="LOW_MARGIN",
                message_id="pricing.alert.low_margin",
                severity="warning",
            )
        )

    # Rule 2 — HIGH_MRP_MULTIPLIER: mrp / input_cost strictly greater than 3.
    # Guard for input_cost == 0 (Pydantic ``gt=0`` should prevent this, but
    # we guard defensively because this helper accepts a Decimal that
    # bypasses the schema gate in unit tests).
    if input_cost > Decimal("0"):
        multiplier = breakdown.mrp / input_cost
        if multiplier > _HIGH_MRP_MULTIPLIER:
            alerts.append(
                PricingAlert(
                    code="HIGH_MRP_MULTIPLIER",
                    message_id="pricing.alert.high_mrp_multiplier",
                    severity="warning",
                )
            )

    # Rule 3 — THIN_PROFIT: profit (INR) strictly less than 50.
    if breakdown.profit < _THIN_PROFIT_THRESHOLD:
        alerts.append(
            PricingAlert(
                code="THIN_PROFIT",
                message_id="pricing.alert.thin_profit",
                severity="info",
            )
        )

    return alerts


def _q(value: Decimal) -> Decimal:
    """Quantize a Decimal to 2 dp with banker's rounding.

    Centralised so every monetary surface in this module is rounded
    identically per §12.B.1 step 6 + CLAUDE.md numeric precision rule.
    """
    return value.quantize(_TWO_PLACES, rounding=ROUND_HALF_EVEN)


__all__ = [
    "calculate",
    "get_last_calc",
    # Pure-function exports for unit-tests (NOT part of the cross-module
    # surface — §16 callers must use ``calculate`` / ``get_last_calc``).
    "_compute_pnl",
    "_generate_alerts",
    "DEFAULT_GST_PCT",
]
