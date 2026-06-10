"""``category`` repository — module-private SQLAlchemy 2.0 typed reads.

Per BACKEND_ARCHITECTURE.md §9.D (LOCKED 2026-06-05).

Module-private rule (§16)
-------------------------
These functions are NOT importable by other modules.  Cross-module code
that needs category info MUST call :mod:`app.modules.category.service`
methods — NEVER ``from app.modules.category.repository import ...``.
The §19 import-linter contract pins this.

Global-data carve-out (§4.C)
----------------------------
``categories`` / ``templates`` / ``field_enum_values`` / ``field_aliases``
are GLOBAL reference data per §4.C + ``MVP_ARCH §10.2``.  **NO**
``scope_to_user(user_id)`` call appears in this module — the §19 linter
exception lists these tables in ``core/tenancy._GLOBAL_TABLES``.
This is the one explicit deviation from the "every owned-table query has
``user_id`` in signature" rule.

Read-only at runtime
--------------------
The seed-time tables this module reads are populated by the DATABASE
track (per §0.D + §2.3).  Backend NEVER issues INSERT/UPDATE/DELETE
against them at runtime.  Every method below is a SELECT.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.category.domain import CategoryRow, SuperCategoryInfo
from app.modules.category.exceptions import (
    CategoryNotFoundError,
    FieldEnumNotFoundError,
)
from app.shared.models.category import Category as CategoryORM
from app.shared.models.field_enum_value import FieldEnumValue as FieldEnumValueORM
from app.shared.models.template import Template as TemplateORM

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _orm_to_row(row: CategoryORM) -> CategoryRow:
    """Convert a hydrated :class:`CategoryORM` to the frozen :class:`CategoryRow`."""
    return CategoryRow(
        id=row.id,
        meesho_leaf_id=row.meesho_leaf_id,
        super_id=row.super_id,
        super_name=row.super_name,
        path=row.path,
        leaf_name=row.leaf_name,
        template_id=row.template_id,
        commission_pct=row.commission_pct,
    )


# ─────────────────────────────────────────────────────────────────────────────
# §9.D methods (7)
# ─────────────────────────────────────────────────────────────────────────────
async def search_via_trigram(
    db: AsyncSession,
    q: str | None,
    super_id: str | None,
    limit: int,
    offset: int,
) -> tuple[list[CategoryRow], int]:
    """pg_trgm ILIKE search against the 3 GIN indexes shipped in migration
    ``a1b2c3d4e5f6`` per ``MVP_ARCH §7.4`` + §7.6 ranking.

    Triggers ``Bitmap Index Scan on idx_categories_path_trgm`` (or the
    ``leaf_name_trgm``/``super_name_trgm`` siblings) when ``q`` is supplied.
    When ``q`` is None the query degrades to a plain super_id-filtered
    page scan.

    Ranking: ``similarity(path, :q)`` DESC (pg_trgm score).  When ``q``
    is None or empty the similarity column is fixed at 0.0 so the result
    set still carries the ``similarity`` field consistently for the
    service-layer schema.

    Args:
        db: AsyncSession.
        q: Search query (1-100 chars, optional).
        super_id: Super-category filter (optional).
        limit: Page size (1-100 per §9.E ``BrowseQuery``).
        offset: Page offset (>= 0).

    Returns:
        ``(rows, total_count)`` — rows is the current page, total_count
        is the TOTAL matching row count across all pages.
    """
    # Build the WHERE clause.
    conditions = []
    if q is not None and q.strip():
        like_pattern = f"%{q}%"
        conditions.append(
            (CategoryORM.path.ilike(like_pattern))
            | (CategoryORM.leaf_name.ilike(like_pattern))
            | (CategoryORM.super_name.ilike(like_pattern))
        )
    if super_id is not None and super_id != "":
        conditions.append(CategoryORM.super_id == super_id)

    # Page query with similarity ranking.
    if q is not None and q.strip():
        # similarity(path, :q) — pg_trgm function — sorted DESC so the
        # GIN indexes can drive the bitmap scan + the result ordering is
        # the documented relevance contract per `MVP_ARCH §7.6`.
        similarity_expr = func.similarity(CategoryORM.path, q).label("sim")
    else:
        # No search query — similarity not meaningful; fixed 0.0.
        similarity_expr = func.cast(0.0, type_=CategoryORM.commission_pct.type).label(
            "sim"
        )

    page_stmt = select(CategoryORM, similarity_expr)
    if conditions:
        for cond in conditions:
            page_stmt = page_stmt.where(cond)
    if q is not None and q.strip():
        page_stmt = page_stmt.order_by(similarity_expr.desc(), CategoryORM.leaf_name)
    else:
        page_stmt = page_stmt.order_by(CategoryORM.super_id, CategoryORM.leaf_name)
    page_stmt = page_stmt.limit(limit).offset(offset)

    page_result = await db.execute(page_stmt)
    rows: list[CategoryRow] = [_orm_to_row(orm_row) for orm_row, _sim in page_result.all()]

    # Total-count query (uncached at the repository — the service layer
    # caches the BrowseResponse as a whole per `(q, super_id, limit, offset)`).
    count_stmt = select(func.count()).select_from(CategoryORM)
    if conditions:
        for cond in conditions:
            count_stmt = count_stmt.where(cond)
    count_result = await db.execute(count_stmt)
    total = int(count_result.scalar_one() or 0)

    return rows, total


async def fetch_category_tree(db: AsyncSession) -> list[CategoryRow]:
    """Flat list of all 3,772 ``categories`` rows ordered by super_id, leaf_name.

    Used by:
    * ``service.get_category_tree`` — in-Python group-by super_id assembly.
    * ``service.suggest_categories`` — passed through the picker's
      ``compress_tree`` helper (per §9.B.1 flow step 3).

    Single query — no JOIN.  Repo-level caching is the caller's
    responsibility (the service caches the tree at TTL 1 h per §9.I).
    """
    stmt = select(CategoryORM).order_by(CategoryORM.super_id, CategoryORM.leaf_name)
    result = await db.execute(stmt)
    return [_orm_to_row(orm_row) for orm_row in result.scalars().all()]


async def fetch_schema_uncached(
    db: AsyncSession,
    category_id: UUID,
) -> dict:
    """JOIN ``categories`` → ``templates`` on ``template_id``; return the
    §5A.B envelope.

    Returned shape merges ``templates.schema_jsonb`` (the field array +
    counts) with the separate ``templates.compliance_shape`` column —
    per §5A.B the envelope's 7th key (``compliance_shape``) is materialised
    here at read time rather than embedded in the JSONB blob.  Seed-time
    rationale: ``compliance_shape`` is a STRUCTURAL flag that gates the
    Export Adapter strategy and benefits from being indexable
    independently of the JSONB.

    Raises:
        CategoryNotFoundError: when ``category_id`` does not exist in
            ``categories``.

    Returns the §5A.B 7-key envelope as a plain ``dict``.
    """
    stmt = (
        select(TemplateORM.schema_jsonb, TemplateORM.compliance_shape)
        .join(CategoryORM, CategoryORM.template_id == TemplateORM.id)
        .where(CategoryORM.id == category_id)
    )
    result = await db.execute(stmt)
    row = result.one_or_none()
    if row is None:
        raise CategoryNotFoundError()
    schema, compliance_shape = row
    # Defensive copy — JSONB columns are sometimes returned as mutable
    # mappings shared with the SA identity map; the cache layer JSON-
    # serialises so this is paranoia but cheap.
    envelope = dict(schema or {})
    # Materialise the §5A.B 7th key from the dedicated column.
    envelope["compliance_shape"] = compliance_shape or "standard"
    return envelope


async def fetch_field_enum_uncached(
    db: AsyncSession,
    category_id: UUID,
    field_name: str,
) -> tuple[list[dict], bool]:
    """SELECT ``enum_entries``, ``truncated`` FROM ``field_enum_values``
    WHERE ``(category_id, field_name)`` matches.

    Validates that ``category_id`` exists in ``categories`` first so that
    a missing category raises :class:`CategoryNotFoundError` (404 with
    ``category.lookup.not_found``) rather than the less specific
    :class:`FieldEnumNotFoundError`.

    Raises:
        CategoryNotFoundError: when ``category_id`` does not exist.
        FieldEnumNotFoundError: when ``(category_id, field_name)`` has no
            row in ``field_enum_values``.

    Returns:
        ``(enum_entries_list, truncated_bool)``.
    """
    # Validate category_id existence first — gives the cleaner 404 with
    # the category-not-found envelope (caller knows to surface the picker
    # again rather than refresh the field-enum endpoint).
    exists = await assert_category_exists_uncached(db, category_id)
    if not exists:
        raise CategoryNotFoundError()

    stmt = select(FieldEnumValueORM.enum_entries, FieldEnumValueORM.truncated).where(
        FieldEnumValueORM.category_id == category_id,
        FieldEnumValueORM.field_name == field_name,
    )
    result = await db.execute(stmt)
    row = result.one_or_none()
    if row is None:
        raise FieldEnumNotFoundError()
    enum_entries, truncated = row
    # JSONB → list[dict] (paranoid coercion in case the driver hands back
    # a sequence type that doesn't json.dumps cleanly).
    if enum_entries is None:
        entries_list: list[dict] = []
    elif isinstance(enum_entries, list):
        entries_list = [dict(e) if isinstance(e, dict) else e for e in enum_entries]
    else:
        # Defensive — schema is list-of-objects per §5.6.4 but be tolerant.
        entries_list = list(enum_entries)  # type: ignore[arg-type]
    return entries_list, bool(truncated)


async def list_super_id_distinct(db: AsyncSession) -> list[SuperCategoryInfo]:
    """Distinct super_id / super_name / COUNT(*) aggregate.

    Drives ``customer.service.set_active_categories`` validation (via the
    cross-module ``service.list_super_categories``) and the dashboard /
    seller-onboarding UI hint counters.

    Returns rows sorted by ``super_id`` ASCENDING (stable contract for
    cache + tests).
    """
    stmt = (
        select(
            CategoryORM.super_id,
            CategoryORM.super_name,
            func.count(CategoryORM.id).label("leaf_count"),
        )
        .group_by(CategoryORM.super_id, CategoryORM.super_name)
        .order_by(CategoryORM.super_id)
    )
    result = await db.execute(stmt)
    return [
        SuperCategoryInfo(
            super_id=str(super_id),
            super_name=str(super_name),
            leaf_count=int(leaf_count),
        )
        for super_id, super_name, leaf_count in result.all()
    ]


async def get_commission_uncached(
    db: AsyncSession,
    category_id: UUID,
) -> Decimal | None:
    """Return ``categories.commission_pct`` for ``category_id``.

    Returns ``None`` when the row is absent OR when ``commission_pct``
    itself is NULL.  The service-layer ``get_commission`` translates
    no-row → :class:`CategoryNotFoundError`; missing commission stays
    None (pricing service interprets None as "no commission rule
    seeded").
    """
    stmt = select(CategoryORM.commission_pct).where(CategoryORM.id == category_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def assert_category_exists_uncached(
    db: AsyncSession,
    category_id: UUID,
) -> bool:
    """``SELECT 1 FROM categories WHERE id = :id LIMIT 1`` — bare existence check.

    Used both by:
    * ``service.assert_category_exists`` (catalog draft-creation gate per §10), and
    * the Smart Picker Layer 2 guardrail final-pass validation per
      §9.B.1 flow step 3 (each AI-returned ``category_id`` must exist).

    Returns:
        ``True`` if the row exists; ``False`` otherwise.  Never raises.
    """
    stmt = select(CategoryORM.id).where(CategoryORM.id == category_id).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


__all__ = [
    "assert_category_exists_uncached",
    "fetch_category_tree",
    "fetch_field_enum_uncached",
    "fetch_schema_uncached",
    "get_commission_uncached",
    "list_super_id_distinct",
    "search_via_trigram",
]
