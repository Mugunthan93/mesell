"""``pricing`` repository — module-private SQLAlchemy 2.0 typed CRUD over
``pricing.pricing_calcs``.

Per BACKEND_ARCHITECTURE.md §12.D (LOCKED 2026-06-05).  Vendored into svc-pricing
(spec §3.A) with the §0.6 ``products``-JOIN rewritten OUT.

§0.6 RESOLUTION — the ``products`` JOIN is GONE (Option B)
---------------------------------------------------------
The monolith :func:`find_latest_by_product` JOINed ``products`` with
``Product.user_id == user_id`` to user-scope the read inside the SQL
(repository.py:147-155).  After extraction ``products`` is a CATALOG-owned
table in another schema — that JOIN is an illegal cross-schema query (§2.D
HTTP-only).  It is REMOVED here.  User-scoping is enforced UPSTREAM at the
catalog ``assert_product_ownership`` HTTP shim, which ``service.get_last_calc``
calls (service.py:241) BEFORE this read — so by the time we reach the DB the
product is proven to belong to the caller.  The query is now a simple
``WHERE pricing_calcs.product_id = :product_id ORDER BY created_at DESC
LIMIT 1`` with NO reference to ``products``.

The ``user_id`` parameter is RETAINED on the :func:`find_latest_by_product`
signature for intra-module call-site parity (``service.get_last_calc`` calls
``find_latest_by_product(db, user_id, product_id)`` at service.py:242) and is
documented as "tenancy enforced upstream"; it no longer reaches the SQL.

Module-private rule (§16)
-------------------------
These functions are NOT importable by other modules.

DECISION FLAG §12-PRICING-D4 — DDL is the law
---------------------------------------------
The actual ``pricing_calcs`` DDL (Wave 1 LOCKED §5.E ORM registry) does NOT
carry a ``user_id`` column.  Tenant isolation is enforced through the
``product_id → products.user_id`` chain — asserted at the catalog ownership
shim upstream.  The §19 CI ``check_scope_to_user`` scanner allowlists
``app.modules.pricing.repository.insert_calc`` (tests/lint/check_scope_to_user.py:78)
because ``pricing_calcs`` has no ``user_id`` column and the tenancy gate is
upstream — that allowlist entry is carried into the svc-pricing context.

Append-only invariant (§12.B.1 step 8)
--------------------------------------
``pricing_calcs`` is an audit trail.  :func:`insert_calc` is the only mutator;
no UPDATE method exists.  Each price calculation creates a NEW row.

Transactions
------------
No transaction blocks inside repository methods — transactions are owned by
``service.py`` per the §4.G commit-then-audit invariant (M8).  The repository
calls ``db.flush()`` so the service can read back identity-mapped fields; the
route ``Depends(get_db)`` handles commit / rollback.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import PricingCalc
from app.shared.models.pricing_calc import PricingCalc as PricingCalcORM

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
    """SELECT the most recent ``pricing_calcs`` row for ``product_id``.

    Backing query for :func:`service.get_last_calc`.  ``ORDER BY created_at
    DESC LIMIT 1``.

    §0.6: the monolith JOINed ``products`` to user-scope this read inside the
    SQL.  That JOIN is REMOVED (``products`` is catalog-owned, another schema —
    illegal cross-schema query).  User-scoping is enforced UPSTREAM at the
    catalog ``assert_product_ownership`` HTTP shim, which
    ``service.get_last_calc`` calls (service.py:241) BEFORE this read.  The
    ``user_id`` parameter is retained for intra-module call-site parity but no
    longer reaches the SQL.

    Returns ``None`` if no calc has been run for ``product_id``.
    """
    stmt = (
        select(PricingCalcORM)
        .where(PricingCalcORM.product_id == product_id)
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
