"""``monitor`` repository — PRIVATE DB reads for the dedupe gate.

All functions are read-only. They use the index
``idx_category_snapshot_latest`` on ``(category_id, captured_at)`` (W1) for
the "latest / second-latest snapshot" lookups, and the
``idx_categories_meesho_leaf`` path for the category scrape-input lookup.

Tenancy note
------------
``category_snapshots`` and ``categories`` are GLOBAL tables (no ``user_id``
column) — the category monitor is a platform-level background job, not a
per-seller request. The §16.F.2 ``scope_to_user`` AST scanner excludes
global-table repositories (``category`` is on its allowlist); ``monitor``
follows the same posture. There is no per-user scoping to apply here.

This module is PRIVATE to ``monitor`` per §16.C Rule 2 — only
``monitor.service`` imports it.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.category import Category
from app.shared.models.category_snapshot import CategorySnapshot
from app.shared.models.notification import Notification
from app.shared.models.product import Product

logger = logging.getLogger(__name__)


async def get_latest_snapshot(
    db: AsyncSession,
    category_id: UUID,
) -> CategorySnapshot | None:
    """Return the most-recent ``category_snapshots`` row for ``category_id``.

    Drives the TTL freshness guard: the caller compares ``captured_at``
    against ``now(UTC) - CATEGORY_SNAPSHOT_TTL_SECONDS``.

    Uses ``idx_category_snapshot_latest`` (``category_id, captured_at DESC``).
    Returns ``None`` when the category has never been snapshotted.
    """
    result = await db.execute(
        select(CategorySnapshot)
        .where(CategorySnapshot.category_id == category_id)
        .order_by(CategorySnapshot.captured_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_prior_snapshot(
    db: AsyncSession,
    category_id: UUID,
) -> CategorySnapshot | None:
    """Return the SECOND-most-recent snapshot row for ``category_id``.

    After a fresh scrape inserts a new row, the "prior" snapshot is the
    one immediately before it (``OFFSET 1``). Its ``dimensions_jsonb`` +
    ``content_hash`` feed :func:`scripts.diff_category_rules.diff_category_snapshot`.

    Returns ``None`` when there is no prior snapshot (first-ever scrape) —
    the caller treats that as "nothing to diff against".
    """
    result = await db.execute(
        select(CategorySnapshot)
        .where(CategorySnapshot.category_id == category_id)
        .order_by(CategorySnapshot.captured_at.desc())
        .offset(1)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_category_scrape_inputs(
    db: AsyncSession,
    category_id: UUID,
) -> tuple[str, str] | None:
    """Resolve a category id to its Meesho scrape inputs.

    Returns ``(meesho_leaf_id, leaf_name)`` — the ``sscat_id`` and
    ``category_name`` arguments :func:`scripts.scrape_category.scrape_category`
    needs. Returns ``None`` when no ``categories`` row matches the id (the
    caller raises :class:`~app.modules.monitor.exceptions.CategoryNotFoundError`).
    """
    result = await db.execute(
        select(Category.meesho_leaf_id, Category.leaf_name).where(
            Category.id == category_id
        )
    )
    row = result.first()
    if row is None:
        return None
    return row[0], row[1]


# ─────────────────────────────────────────────────────────────────────────────
# Wave-4 fan-out reads / writes
# ─────────────────────────────────────────────────────────────────────────────


async def get_category_name(db: AsyncSession, category_id: UUID) -> str | None:
    """Return the human-readable leaf name for ``category_id`` (for copy).

    The ``categories`` table has no ``name`` column; ``leaf_name`` is the
    terminal category display name (e.g. ``"Kurtis"``) used in seller-facing
    copy. Returns ``None`` when the category does not exist.
    """
    result = await db.execute(
        select(Category.leaf_name).where(Category.id == category_id)
    )
    return result.scalar_one_or_none()


async def get_distinct_subscribers(
    db: AsyncSession,
    category_id: UUID,
) -> list[UUID]:
    """Return the distinct ``user_id`` set subscribed to ``category_id``.

    Reads the ``category_subscription`` VIEW (W1 — NOT an ORM table, so a raw
    ``text()`` query). The VIEW is the UNION of catalog-level + (active)
    product-level subscriptions, already ``DISTINCT``. Returns ``[]`` when no
    seller is in the category.
    """
    result = await db.execute(
        text(
            "SELECT DISTINCT user_id FROM category_subscription "
            "WHERE category_id = :cid"
        ),
        {"cid": str(category_id)},
    )
    return [row[0] for row in result.all()]


async def get_user_catalog_ids(
    db: AsyncSession,
    user_id: UUID,
    category_id: UUID,
) -> list[UUID]:
    """Return the distinct catalog ids a user has subscribed to in a category.

    Reads the ``category_subscription`` VIEW (raw ``text()``). Drives the
    "{N} of your catalogs are affected" copy fragment + the notification
    payload's ``affected_catalog_ids``.
    """
    result = await db.execute(
        text(
            "SELECT DISTINCT catalog_id FROM category_subscription "
            "WHERE user_id = :uid AND category_id = :cid"
        ),
        {"uid": str(user_id), "cid": str(category_id)},
    )
    return [row[0] for row in result.all()]


async def flag_user_products(
    db: AsyncSession,
    user_id: UUID,
    category_id: UUID,
    *,
    recheck: bool,
    reprice: bool,
    export: bool,
) -> int:
    """Idempotently SET the requested change-flags on a user's products.

    Updates ``products`` scoped to ``(user_id, category_id)`` and excluding
    soft-deleted rows. Flags are set to ``true`` ONLY — never toggled off —
    so a Celery retry is a no-op on already-flagged rows. When all three flags
    are ``False`` this is a no-op (returns 0) without issuing an UPDATE.

    Returns the number of rows the UPDATE touched.
    """
    values: dict[str, bool] = {}
    if recheck:
        values["needs_recheck"] = True
    if reprice:
        values["needs_reprice"] = True
    if export:
        values["needs_export"] = True
    if not values:
        return 0

    from sqlalchemy import update

    result = await db.execute(
        update(Product)
        .where(
            Product.user_id == user_id,
            Product.category_id == category_id,
            Product.deleted_at.is_(None),
        )
        .values(**values)
    )
    return result.rowcount or 0


async def insert_notification(
    db: AsyncSession,
    user_id: UUID,
    category_id: UUID,
    content_hash: str,
    payload: dict,
) -> bool:
    """Insert one notification row idempotently (ON CONFLICT DO NOTHING).

    The unique constraint ``uq_notification_user_cat_hash``
    ``(user_id, category_id, content_hash)`` makes a Celery retry a no-op:
    a duplicate insert is silently skipped. Returns ``True`` when a NEW row
    was inserted, ``False`` when the row already existed (skipped).
    """
    stmt = (
        pg_insert(Notification)
        .values(
            user_id=user_id,
            category_id=category_id,
            content_hash=content_hash,
            payload_jsonb=payload,
        )
        .on_conflict_do_nothing(constraint="uq_notification_user_cat_hash")
        .returning(Notification.id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None
