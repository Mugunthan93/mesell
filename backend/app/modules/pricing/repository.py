"""``pricing`` repository — module-private SQLAlchemy 2.0 typed CRUD over
``pricing_calcs``.

Per BACKEND_ARCHITECTURE.md §12.D (LOCKED 2026-06-05) as superseded by the
**W2 Price Calculator rework (census-confirmed settlement model, 2026-06-19)**.

Module-private rule (§16)
-------------------------
These functions are NOT importable by other modules.  Cross-module code
that needs pricing data MUST call :mod:`app.modules.pricing.service`
surfaces (e.g. ``get_last_calc``).  The §19 import-linter Contract 1
pins this.

DECISION FLAG §12-PRICING-D4 — DDL is the law
---------------------------------------------
The actual ``pricing_calcs`` DDL carries no ``user_id`` column.  Tenant
isolation is enforced through the ``product_id → products.user_id`` FK
chain — the ORM model docstring states "tenant isolation is enforced
through the product → catalog → user FK chain."

§12.D prose says "use ``scope_to_user(user_id)`` per §4.C on every
query".  Pricing honors the intent by:

1. **Service-layer M6 enforcement** — every call to repository methods
   is gated by ``catalog.assert_product_ownership(product_id, user_id)``
   upstream.
2. **Repository-layer JOIN** — :func:`find_latest_by_product` adds an
   explicit join through ``products`` with ``Product.user_id == user_id``
   so the SQL itself never returns a cross-tenant row even if the
   service-layer gate were bypassed.  This is the structural equivalent
   of the ``scope_to_user`` grep-anchor.
3. **Insert path** — :func:`insert_calc` accepts only the confirmed-model
   monetary columns; the tenancy gate is enforced upstream.

Confirmed-model columns written by W2+ service layer
-----------------------------------------------------
``selling_price``, ``shipping``, ``total_price``, ``commission_pct``,
``commission_fees``, ``gst_on_shipping``, ``tds``, ``tcs``,
``estimated_bank_settlement``, ``meesho_leaf_id``.

The deprecated #285 columns (``mrp``, ``meesho_price``, ``seller_price``,
``gst_pct``, ``margin``, ``margin_pct``, ``estimated_payout``,
``referral_commission``, ``shipping_charge``, ``logistics_fee``,
``fixed_fee``, ``gst_on_fees``, ``rto_expected_loss``, ``return_rate_pct``,
``markup_pct``, ``wdrp_price``) remain nullable in the DDL (Q3 KEEP-NULLABLE
ruling) but are NEVER written by :func:`insert_calc` and are not mapped in
:func:`_orm_to_domain`.

Append-only invariant (§12.B.1 step 8)
--------------------------------------
``pricing_calcs`` is an audit trail.  :func:`insert_calc` is the only
mutator; no UPDATE method exists on this repository.  Each price
calculation creates a NEW row.

Transactions
------------
No transaction blocks inside repository methods — transactions are owned
by ``service.py`` per the §4.G commit-then-audit invariant (M8).  The
repository calls ``db.flush()`` so the service can read back
identity-mapped fields; the route ``Depends(get_db)`` handles commit/rollback.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.pricing.domain import PricingCalc
from app.shared.models.pricing_calc import PricingCalc as PricingCalcORM
from app.shared.models.product import Product as ProductORM

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Writes
# ─────────────────────────────────────────────────────────────────────────────
async def insert_calc(
    db: AsyncSession,
    *,
    product_id: UUID,
    selling_price: Decimal,
    shipping: Decimal,
    total_price: Decimal,
    commission_pct: Decimal,
    commission_fees: Decimal,
    gst_on_shipping: Decimal,
    tds: Decimal,
    tcs: Decimal,
    estimated_bank_settlement: Decimal,
    meesho_leaf_id: str,
) -> PricingCalc:
    """INSERT a new ``pricing_calcs`` row (confirmed model, W2).

    Writes ONLY the confirmed-model columns.  The deprecated #285 columns
    (``mrp``, ``meesho_price``, ``seller_price``, etc.) are intentionally
    absent — they remain nullable in the DDL (Q3) but are never touched
    by this function.

    Called from :func:`service.calculate`.  Tenancy gate is enforced
    upstream — the ``product_id`` MUST belong to the calling user
    (verified by ``catalog.assert_product_ownership`` before the insert).

    Returns:
        The inserted :class:`PricingCalc` domain dataclass — caller
        receives the DB-generated ``id`` + ``created_at`` populated.
    """
    row = PricingCalcORM(
        product_id=product_id,
        selling_price=selling_price,
        shipping=shipping,
        total_price=total_price,
        commission_pct=commission_pct,
        commission_fees=commission_fees,
        gst_on_shipping=gst_on_shipping,
        tds=tds,
        tcs=tcs,
        estimated_bank_settlement=estimated_bank_settlement,
        meesho_leaf_id=meesho_leaf_id,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    logger.debug(
        "pricing_calcs INSERT product_id=%s leaf=%s settlement=%s",
        product_id,
        meesho_leaf_id,
        estimated_bank_settlement,
    )
    return _orm_to_domain(row)


# ─────────────────────────────────────────────────────────────────────────────
# Reads
# ─────────────────────────────────────────────────────────────────────────────
async def find_latest_by_product(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
) -> PricingCalc | None:
    """SELECT the most recent ``pricing_calcs`` row for ``product_id``,
    scoped to ``user_id`` via JOIN through ``products``.

    Backing query for :func:`service.get_last_calc`.  ``ORDER BY
    created_at DESC LIMIT 1``.  Joins ``products`` so the SQL itself
    filters cross-tenant rows even if the upstream service gate were
    bypassed (§12-PRICING-D4 grep anchor).

    Returns ``None`` if no calc has been run for ``product_id``, OR the
    product is soft-deleted, OR the product belongs to another user.
    """
    stmt = (
        select(PricingCalcORM)
        .join(ProductORM, PricingCalcORM.product_id == ProductORM.id)
        .where(ProductORM.user_id == user_id)
        .where(PricingCalcORM.product_id == product_id)
        .where(ProductORM.deleted_at.is_(None))
        .order_by(PricingCalcORM.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return _orm_to_domain(row)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────
def _orm_to_domain(row: PricingCalcORM) -> PricingCalc:
    """Map ORM row → frozen domain dataclass (confirmed-model columns only).

    The deprecated #285 columns are intentionally absent from the domain
    shape and from this mapping.
    """
    return PricingCalc(
        id=row.id,
        product_id=row.product_id,
        selling_price=row.selling_price,
        shipping=row.shipping,
        total_price=row.total_price,
        commission_pct=row.commission_pct,
        commission_fees=row.commission_fees,
        gst_on_shipping=row.gst_on_shipping,
        tds=row.tds,
        tcs=row.tcs,
        estimated_bank_settlement=row.estimated_bank_settlement,
        meesho_leaf_id=row.meesho_leaf_id or "",
        created_at=row.created_at,
    )


__all__ = [
    "insert_calc",
    "find_latest_by_product",
]
