"""``pricing`` repository — module-private SQLAlchemy 2.0 typed CRUD over
``pricing_calcs``.

Per BACKEND_ARCHITECTURE.md §12.D (LOCKED 2026-06-05).

Module-private rule (§16)
-------------------------
These functions are NOT importable by other modules.  Cross-module code
that needs pricing data MUST call :mod:`app.modules.pricing.service`
surfaces (e.g. ``get_last_calc``).  The §19 import-linter Contract 1
pins this.

DECISION FLAG §12-PRICING-D4 — DDL is the law
---------------------------------------------
The actual ``pricing_calcs`` DDL (Wave 1 LOCKED §5.E ORM registry) does
NOT carry a ``user_id`` column.  Tenant isolation is enforced through
the ``product_id → products.user_id`` FK chain — the §5.E ORM model
docstring explicitly states "tenant isolation is enforced through the
product → catalog → user FK chain. Service layer always resolves via
product (which carries user_id) before querying pricing_calcs."

§12.D prose says "use ``scope_to_user(user_id)`` per §4.C on every
query".  Pricing cannot apply :func:`scope_to_user` to a bare
``select(PricingCalc)`` because ``PricingCalc`` has no ``user_id``
column.  We honor the intent by:

1. **Service-layer M6 enforcement** — every call to repository methods
   on ``pricing_calcs`` is gated by
   ``catalog.assert_product_ownership(product_id, user_id)`` upstream
   (see ``service.calculate`` + ``service.get_last_calc``).
2. **Repository-layer JOIN** — :func:`find_latest_by_product` adds an
   explicit join through ``products`` with ``Product.user_id ==
   user_id`` so the SQL itself never returns a cross-tenant row even if
   the service-layer gate were bypassed.  This is the structural
   equivalent of the ``scope_to_user`` grep-anchor.
3. **Insert path** — :func:`insert_calc` accepts the structured monetary
   columns directly; the tenancy gate is enforced upstream in
   ``service.calculate``.

The §19 CI tenancy scanner sees the explicit ``user_id`` predicate on
the JOIN as the §16 grep-anchor for this module.

Append-only invariant (§12.B.1 step 8)
--------------------------------------
``pricing_calcs`` is an audit trail.  :func:`insert_calc` is the only
mutator; no UPDATE method exists on this repository.  Each price
calculation creates a NEW row.

Transactions
------------
No transaction blocks inside repository methods — transactions are
owned by ``service.py`` per the §4.G commit-then-audit invariant (M8).
The repository calls ``db.flush()`` so the service can read back
identity-mapped fields; the test fixture / route ``Depends(get_db)``
handles commit / rollback.
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
    mrp: Decimal,
    meesho_price: Decimal,
    seller_price: Decimal,
    commission_pct: Decimal,
    gst_pct: Decimal,
    margin: Decimal,
    margin_pct: Decimal,
) -> PricingCalc:
    """INSERT a new ``pricing_calcs`` row.

    Called from :func:`service.calculate` step 8.  Tenancy gate is
    enforced upstream — the ``product_id`` MUST belong to the calling
    user (verified by ``catalog.assert_product_ownership`` before the
    insert).

    Args:
        db: Async session bound to the request transaction.
        product_id: FK to ``products.id`` (validated upstream).
        mrp: Maximum Retail Price (quantized to 2 dp).
        meesho_price: Listing price on Meesho (V1: equal to MRP).
        seller_price: Amount Meesho remits net of commission + GST.
        commission_pct: Commission rate applied (from
            ``category.get_commission``).
        gst_pct: GST rate applied (V1: constant 18%).
        margin: Absolute profit in INR (seller_price − input_cost).
        margin_pct: Profit as percentage of input_cost.

    Returns:
        The inserted :class:`PricingCalc` domain dataclass — caller
        receives the DB-generated ``id`` + ``created_at`` populated.
    """
    row = PricingCalcORM(
        product_id=product_id,
        mrp=mrp,
        meesho_price=meesho_price,
        seller_price=seller_price,
        commission_pct=commission_pct,
        gst_pct=gst_pct,
        margin=margin,
        margin_pct=margin_pct,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
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
    bypassed.

    Returns ``None`` if no calc has been run for ``product_id`` OR the
    product is soft-deleted OR the product belongs to another user.
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
    """Map ORM row → frozen domain dataclass."""
    return PricingCalc(
        id=row.id,
        product_id=row.product_id,
        mrp=row.mrp,
        meesho_price=row.meesho_price,
        seller_price=row.seller_price,
        commission_pct=row.commission_pct,
        gst_pct=row.gst_pct,
        margin=row.margin,
        margin_pct=row.margin_pct,
        created_at=row.created_at,
    )


__all__ = [
    "insert_calc",
    "find_latest_by_product",
]
