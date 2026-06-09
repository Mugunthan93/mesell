"""``catalog`` repository — module-private SQLAlchemy 2.0 typed CRUD over
``catalogs`` / ``products`` / ``product_drafts``.

Per BACKEND_ARCHITECTURE.md §10.D (LOCKED 2026-06-05).

Module-private rule (§16)
-------------------------
These functions are NOT importable by other modules.  Cross-module code
that needs catalog data MUST call :mod:`app.modules.catalog.service`
surfaces.  The §19 import-linter Contract 1 pins this.

Tenancy (§4.C — locked)
-----------------------
Every method on an owned table (``catalogs`` / ``products`` /
``product_drafts``) passes through
:func:`app.core.tenancy.scope_to_user`.  The ``scope_to_user`` invocation
is the §19 grep-anchor that proves the tenancy invariant holds.

Soft-delete invariant
---------------------
``find_by_id`` filters ``deleted_at IS NULL`` so the cross-module
:func:`assert_product_ownership` cannot leak a soft-deleted product.
``soft_delete_product`` is the only mutator that touches ``deleted_at``.

Autosave wrapper (DECISION FLAG §10-CATALOG-D1 applied)
-------------------------------------------------------
The ``product_drafts`` table per migration ``935e55b4852c`` carries only
``(user_id, product_id, draft_jsonb, saved_at)``.  Per master ruling
2026-06-07 we embed §10.D's ``fields`` + ``autosave_count`` inside
``draft_jsonb`` as a wrapper envelope::

    draft_jsonb = {"fields": <merged_fields_dict>,
                   "autosave_count": <int>}

Legacy rows that lack the wrapper coerce on read to
``autosave_count=1`` and ``fields=<draft_jsonb>``.

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
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, literal_column, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import scope_to_user
from app.shared.models.catalog import Catalog as CatalogORM
from app.shared.models.product import Product as ProductORM
from app.shared.models.product_draft import ProductDraft as ProductDraftORM

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Product reads
# ─────────────────────────────────────────────────────────────────────────────
async def find_by_id(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
) -> ProductORM | None:
    """SELECT a product by ID, scoped to the caller AND filtering soft-deletes.

    Returns ``None`` for any of:

    * row does not exist,
    * row exists but belongs to another ``user_id``,
    * row exists, belongs to caller, but ``deleted_at IS NOT NULL``.

    All three cases collapse to ``None`` so the caller (typically
    :func:`service.assert_product_ownership`) raises
    :class:`exceptions.ProductNotFoundError` uniformly.
    """
    stmt = (
        scope_to_user(select(ProductORM), user_id)
        .where(ProductORM.id == product_id)
        .where(ProductORM.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def find_by_id_including_deleted(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
) -> ProductORM | None:
    """SELECT a product by ID, scoped to caller, INCLUDING soft-deletes.

    Used only by the soft-delete idempotency check
    (:func:`service.soft_delete`) — a second DELETE on an already-deleted
    product still 204s, not 404s, when the caller can prove ownership.
    Distinct from :func:`find_by_id` which collapses soft-deletes to 404.
    """
    stmt = (
        scope_to_user(select(ProductORM), user_id)
        .where(ProductORM.id == product_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def count_active_products(db: AsyncSession, user_id: UUID) -> int:
    """COUNT(*) of non-deleted products for the plan_guard ``product_count``
    gate per §10.B.1 step 1.

    NOTE: :func:`app.core.plan_guard.enforce_plan_limit` re-issues the
    same COUNT internally (it can't depend on a domain repository).  Both
    code paths return the same value because both apply
    ``WHERE deleted_at IS NULL`` against the tenant.  We expose this
    helper for service-layer testing + the §10.J unit tests.
    """
    stmt = (
        scope_to_user(select(func.count(ProductORM.id)), user_id)
        .where(ProductORM.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    return int(result.scalar_one() or 0)


# ─────────────────────────────────────────────────────────────────────────────
# Catalog reads + writes
# ─────────────────────────────────────────────────────────────────────────────
async def find_catalog_by_id(
    db: AsyncSession,
    user_id: UUID,
    catalog_id: UUID,
) -> CatalogORM | None:
    """SELECT a catalog by ID, scoped to caller."""
    stmt = (
        scope_to_user(select(CatalogORM), user_id)
        .where(CatalogORM.id == catalog_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_catalog(
    db: AsyncSession,
    user_id: UUID,
    name: str,
) -> CatalogORM:
    """INSERT a catalog row owned by ``user_id``.

    Used by :func:`service.create_product` when the seller did not pass a
    ``catalog_id`` — the service synthesises a seller-readable default
    name per §10.B.1.
    """
    row = CatalogORM(
        user_id=user_id,
        name=name,
        status="draft",
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


# ─────────────────────────────────────────────────────────────────────────────
# Product writes
# ─────────────────────────────────────────────────────────────────────────────
async def insert_product(
    db: AsyncSession,
    user_id: UUID,
    catalog_id: UUID,
    category_id: UUID,
    name: str | None,
) -> ProductORM:
    """INSERT a fresh product in ``draft`` status.

    Defaults align with §10.B.1 step 5: ``fields_jsonb={}``,
    ``ai_suggestions_jsonb={}``, ``status="draft"``, ``deleted_at=None``.
    The server_defaults on ``created_at`` / ``updated_at`` populate
    timestamps; ``db.refresh`` reads them back so the service returns a
    fully-hydrated row.
    """
    row = ProductORM(
        user_id=user_id,
        catalog_id=catalog_id,
        category_id=category_id,
        name=name,
        status="draft",
        fields_jsonb={},
        ai_suggestions_jsonb={},
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def update_fields_jsonb(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
    patch_dict: dict[str, Any],
) -> ProductORM:
    """JSONB-shallow-merge ``patch_dict`` into ``products.fields_jsonb``
    per §10.D + §10.B.2 step 5.

    Uses the Postgres ``||`` JSONB concatenation operator at the SQL
    layer so the merge is atomic on the DB side (one UPDATE statement)
    and does not require a round-trip + read-modify-write.

    Tenancy: ``WHERE id = :pid AND user_id = :uid AND deleted_at IS NULL``
    via :func:`scope_to_user`.  Returns the refreshed ORM row.
    """
    if not patch_dict:
        # Nothing to merge — fall back to a simple touch of updated_at so
        # the row instance remains valid for service.refresh.
        row = await find_by_id(db, user_id, product_id)
        if row is None:
            raise ValueError(
                f"catalog.repo.update_fields_jsonb: no row for "
                f"user_id={user_id} product_id={product_id}"
            )
        row.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(row)
        return row

    # Cast the bound parameter so Postgres treats it as JSONB even when the
    # SQLAlchemy preparer renders it as text.  ``literal_column`` would also
    # work but ``bindparam`` + ``type_=JSONB`` is the canonical pattern.
    from sqlalchemy import bindparam

    stmt = (
        update(ProductORM)
        .where(ProductORM.id == product_id)
        .where(ProductORM.user_id == user_id)
        .where(ProductORM.deleted_at.is_(None))
        .values(
            fields_jsonb=ProductORM.fields_jsonb.op("||")(
                bindparam("patch", value=patch_dict, type_=JSONB)
            ),
            updated_at=literal_column("NOW()"),
        )
        .returning(ProductORM.id)
    )
    result = await db.execute(stmt)
    returned_id = result.scalar_one_or_none()
    if returned_id is None:
        raise ValueError(
            f"catalog.repo.update_fields_jsonb: no row for "
            f"user_id={user_id} product_id={product_id}"
        )

    # Read back the merged row via tenancy-scoped find — keeps the
    # scope_to_user grep anchor at every read site.
    row = await find_by_id(db, user_id, product_id)
    if row is None:
        raise ValueError(
            f"catalog.repo.update_fields_jsonb: row vanished after UPDATE "
            f"for user_id={user_id} product_id={product_id}"
        )
    return row


async def update_status(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
    new_status: str,
) -> ProductORM:
    """Set ``products.status`` to ``"draft"`` or ``"ready"``.

    Called by :func:`service.patch_product` step 6 when the request
    carries an explicit ``status`` transition.  Returns the refreshed row.
    """
    row = await find_by_id(db, user_id, product_id)
    if row is None:
        raise ValueError(
            f"catalog.repo.update_status: no row for "
            f"user_id={user_id} product_id={product_id}"
        )
    row.status = new_status
    row.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(row)
    return row


async def update_ai_suggestions_jsonb(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
    suggestions_dict: dict[str, Any],
) -> ProductORM:
    """OVERWRITE ``products.ai_suggestions_jsonb`` (each autofill replaces).

    Per §10.D: this is a full replace, NOT a merge — the
    ``ai_suggestions_jsonb`` column carries provenance for the LATEST
    Auto-fill call only.  History lives in ``audit_events``.
    """
    row = await find_by_id(db, user_id, product_id)
    if row is None:
        raise ValueError(
            f"catalog.repo.update_ai_suggestions_jsonb: no row for "
            f"user_id={user_id} product_id={product_id}"
        )
    row.ai_suggestions_jsonb = suggestions_dict
    row.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(row)
    return row


async def soft_delete_product(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
) -> None:
    """Set ``products.deleted_at = NOW()`` per §10.B.5.

    Idempotent: re-deleting a soft-deleted product is a no-op (the WHERE
    clause filters ``deleted_at IS NULL``).  Returns ``None``; route
    sends 204.
    """
    stmt = (
        update(ProductORM)
        .where(ProductORM.id == product_id)
        .where(ProductORM.user_id == user_id)
        .where(ProductORM.deleted_at.is_(None))
        .values(
            deleted_at=literal_column("NOW()"),
            updated_at=literal_column("NOW()"),
        )
    )
    await db.execute(stmt)
    # Defensive flush — keeps deletion visible to any subsequent read in
    # the same transaction (the route's commit happens at request end).
    await db.flush()


# ─────────────────────────────────────────────────────────────────────────────
# Product list (cross-module: dashboard)
# ─────────────────────────────────────────────────────────────────────────────
async def list_paginated(
    db: AsyncSession,
    user_id: UUID,
    *,
    page: int,
    limit: int,
) -> tuple[list[ProductORM], int]:
    """Return (rows, total_count) for active products.

    Offset pagination per §10.E.  Ordering: most-recently-updated first
    so the dashboard surfaces in-progress drafts at the top.

    Caller is responsible for translating the ``page=1, limit=20`` shape
    into ``OFFSET`` (``page-1`` * ``limit``).
    """
    offset = max(0, (page - 1) * limit)
    rows_stmt = (
        scope_to_user(select(ProductORM), user_id)
        .where(ProductORM.deleted_at.is_(None))
        .order_by(ProductORM.updated_at.desc(), ProductORM.id.desc())
        .limit(limit)
        .offset(offset)
    )
    total_stmt = (
        scope_to_user(select(func.count(ProductORM.id)), user_id)
        .where(ProductORM.deleted_at.is_(None))
    )
    rows_result = await db.execute(rows_stmt)
    total_result = await db.execute(total_stmt)
    rows = list(rows_result.scalars().all())
    total = int(total_result.scalar_one() or 0)
    return rows, total


# ─────────────────────────────────────────────────────────────────────────────
# Draft autosave (§10.D §11.6 contract)
# ─────────────────────────────────────────────────────────────────────────────
def _wrap_draft_payload(fields_snapshot: dict[str, Any], autosave_count: int) -> dict[str, Any]:
    """Apply the §10-CATALOG-D1 wrapper shape.

    Centralised so the read-path can apply the inverse coercion in
    exactly one helper (:func:`_unwrap_draft_payload`).
    """
    return {"fields": dict(fields_snapshot), "autosave_count": int(autosave_count)}


def _unwrap_draft_payload(
    draft_jsonb: dict[str, Any] | None,
) -> tuple[dict[str, Any], int]:
    """Return (fields, autosave_count) from a stored ``draft_jsonb``.

    Legacy rows lacking the wrapper coerce to
    ``autosave_count=1`` with ``fields=<draft_jsonb>``.
    """
    if draft_jsonb is None:
        return {}, 1
    if isinstance(draft_jsonb, dict) and "fields" in draft_jsonb:
        fields = draft_jsonb.get("fields") or {}
        if not isinstance(fields, dict):
            fields = {}
        count = draft_jsonb.get("autosave_count", 1)
        try:
            count_int = int(count)
        except (TypeError, ValueError):
            count_int = 1
        return dict(fields), max(1, count_int)
    # Legacy / unwrapped row.
    if isinstance(draft_jsonb, dict):
        return dict(draft_jsonb), 1
    # Defensive — shouldn't happen given the JSONB column type.
    return {}, 1


async def upsert_draft(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
    fields_snapshot: dict[str, Any],
) -> ProductDraftORM:
    """INSERT ... ON CONFLICT DO UPDATE per §10.D + master ruling D1.

    Per ruling: the on-disk DDL has ``(user_id, product_id, draft_jsonb,
    saved_at)``; we embed ``fields`` and ``autosave_count`` inside
    ``draft_jsonb``.  Increment semantics: read existing wrapper +1, or
    1 on first write.

    Returns the refreshed ORM row (so service can read ``saved_at`` for
    the `last_updated` response field).
    """
    # Read existing wrapper (if any) to compute the new autosave_count.
    # No scope_to_user on the read — composite PK is (user_id, product_id);
    # we filter on both, which is equivalent to scope_to_user.
    existing_stmt = select(ProductDraftORM).where(
        ProductDraftORM.user_id == user_id,
        ProductDraftORM.product_id == product_id,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()

    if existing is None:
        next_count = 1
        new_payload = _wrap_draft_payload(fields_snapshot, next_count)
        row = ProductDraftORM(
            user_id=user_id,
            product_id=product_id,
            draft_jsonb=new_payload,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return row

    _, prev_count = _unwrap_draft_payload(existing.draft_jsonb)
    next_count = prev_count + 1
    new_payload = _wrap_draft_payload(fields_snapshot, next_count)
    existing.draft_jsonb = new_payload
    existing.saved_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(existing)
    return existing


async def get_draft(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
) -> ProductDraftORM | None:
    """Read the draft row (or ``None``) for ``(user_id, product_id)``.

    Caller :func:`service.get_draft` handles the 204 / 200 split and
    unwraps the wrapper via :func:`_unwrap_draft_payload`.
    """
    stmt = select(ProductDraftORM).where(
        ProductDraftORM.user_id == user_id,
        ProductDraftORM.product_id == product_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


__all__ = [
    "_unwrap_draft_payload",
    "_wrap_draft_payload",
    "count_active_products",
    "create_catalog",
    "find_by_id",
    "find_by_id_including_deleted",
    "find_catalog_by_id",
    "get_draft",
    "insert_product",
    "list_paginated",
    "soft_delete_product",
    "update_ai_suggestions_jsonb",
    "update_fields_jsonb",
    "update_status",
    "upsert_draft",
]
