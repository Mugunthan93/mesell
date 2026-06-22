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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.category import Category
from app.shared.models.category_snapshot import CategorySnapshot

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
