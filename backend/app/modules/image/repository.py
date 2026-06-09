"""``image`` repository — MODULE-PRIVATE SQLAlchemy queries per §11.D.

Per BACKEND_ARCHITECTURE.md §11.D (LOCKED 2026-06-05).

These methods are NOT importable from other modules per §16 boundary —
every cross-module read of ``product_images`` data goes through
:mod:`.service` (the 4 cross-module surfaces in §11.C).

Tenancy
-------
Every method that touches ``product_images`` joins through
``products.user_id`` and applies :func:`app.core.tenancy.scope_to_user`
on the joined ``Product`` entity.  This is the §19 grep-anchor that
proves the tenancy invariant holds — the ``scope_to_user`` invocation
appears in every method body.

DECISION FLAG §11-IMAGE-D1 (deviation — workaround, not blocker)
----------------------------------------------------------------
§11.D references ``deleted_at IS NULL`` filters + ``SET deleted_at =
NOW()`` writes + ``SET updated_at = NOW()`` writes, but the
``product_images`` ORM model + `MVP_ARCH §2.5` DDL ship neither
``deleted_at`` nor ``updated_at`` columns.  V1 workaround:

* No ``deleted_at`` filter on reads — V1 has no DELETE-image endpoint
  per §11.M; the only soft-delete path is :func:`soft_delete_by_idx`
  which writes ``status='deleted'`` instead of a ``deleted_at`` stamp.
* :func:`find_by_slot` returns ANY row at ``(product_id, order_idx)``
  regardless of soft-delete state — the DB ``UNIQUE(product_id,
  order_idx)`` constraint per `MVP_ARCH §2.5` is the real occupancy
  gate.  A row at the slot → 409 ``ImageSlotOccupiedError``.
* :func:`update_precheck_result` omits the ``updated_at = NOW()`` set
  — only ``precheck_jsonb`` + ``status`` are mutated.
* :func:`soft_delete_by_idx` writes ``status='deleted'`` — internal
  helper only (V1 catalog cascade target; not exposed via any router).

A future ``meesell-database-builder`` dispatch may add the columns; the
repository signatures remain unchanged.  Same pattern as §10
catalog-D1 product_drafts wrapper.
"""

from __future__ import annotations

import logging
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import scope_to_user
from app.modules.image.domain import ImageStatusSummary, ProductImage
from app.shared.models.product import Product as ProductORM
from app.shared.models.product_image import ProductImage as ProductImageORM

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _to_domain(row: ProductImageORM, user_id: UUID) -> ProductImage:
    """Map an ORM row → frozen :class:`ProductImage` domain instance.

    ``user_id`` is supplied by the caller because ``product_images``
    carries no direct ``user_id`` column — the caller asserts ownership
    through the join scope before invoking this mapper.
    """
    return ProductImage(
        id=row.id,
        product_id=row.product_id,
        user_id=user_id,
        gcs_path=row.gcs_path,
        order_idx=row.order_idx,
        is_front=bool(row.is_front),
        width=row.width,
        height=row.height,
        color_space=row.color_space,
        precheck_jsonb=dict(row.precheck_jsonb or {}),
        status=row.status,
        created_at=row.created_at,
    )


def _owned_product_ids_subquery(user_id: UUID, product_id: UUID):
    """Build a tenancy-scoped sub-select of ``products.id`` for
    ``WHERE product_images.product_id IN (...)`` filtering.

    Uses :func:`scope_to_user` against the ``Product`` entity — this is
    the §19 grep-anchor demonstrating tenant scoping for tables (like
    ``product_images``) that have no direct ``user_id`` column.
    """
    return (
        scope_to_user(select(ProductORM.id), user_id)
        .where(ProductORM.id == product_id)
        .where(ProductORM.deleted_at.is_(None))
    )


# ─────────────────────────────────────────────────────────────────────────────
# Writes
# ─────────────────────────────────────────────────────────────────────────────
async def insert(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
    gcs_path: str,
    idx: int,
    width: int,
    height: int,
    color_space: str,
) -> ProductImage:
    """INSERT a row into ``product_images`` per §11.D.

    Pre-conditions enforced UPSTREAM by the caller (service.upload_image):

    * ``catalog.service.assert_product_ownership(product_id, user_id)``
      already raised 404 if the seller does not own the product —
      this method does NOT re-check ownership.
    * No row exists at ``(product_id, idx)`` per :func:`find_by_slot`.
    * Image bytes already written to ``gcs_path``.

    Sets ``status='pending'`` (the server_default) and ``precheck_jsonb=
    {}`` so the Celery worker has a deterministic empty starting state.
    """
    row = ProductImageORM(
        product_id=product_id,
        gcs_path=gcs_path,
        order_idx=idx,
        width=width,
        height=height,
        color_space=color_space,
        precheck_jsonb={},
        # ``status`` server_default = 'pending' per `MVP_ARCH §2.5`
        # ``is_front`` is Computed(persisted=True) — never assigned here.
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return _to_domain(row, user_id=user_id)


async def update_precheck_result(
    db: AsyncSession,
    user_id: UUID,
    image_id: UUID,
    precheck_jsonb: dict,
    status: Literal["ready", "failed_precheck"],
) -> ProductImage:
    """UPDATE ``product_images`` SET precheck_jsonb, status per §11.D.

    Called from the Celery worker context via
    :func:`.service.write_precheck_result`.  Re-validates tenancy via
    the join through ``products.user_id`` — the worker context cannot
    skip the scope_to_user gate even though the user_id is trusted via
    the task payload.

    DECISION FLAG §11-IMAGE-D1 — no ``updated_at`` set (column does not
    exist in V1 schema).
    """
    # Re-scope through products.user_id — same `scope_to_user` anchor
    # as the read methods.  We use a sub-select rather than a JOIN on
    # UPDATE because asyncpg + SQLAlchemy multi-table UPDATEs are
    # finicky; the IN-subquery pattern is portable.
    owned_product_ids = scope_to_user(select(ProductORM.id), user_id)
    stmt = (
        update(ProductImageORM)
        .where(ProductImageORM.id == image_id)
        .where(ProductImageORM.product_id.in_(owned_product_ids))
        .values(precheck_jsonb=precheck_jsonb, status=status)
        .returning(ProductImageORM)
    )
    result = await db.execute(stmt)
    updated = result.scalar_one_or_none()
    if updated is None:
        # Either image_id does not exist or tenant scope rejected.
        # Service layer translates None → ImageNotFoundError.
        raise LookupError(
            f"update_precheck_result: image {image_id!s} not found under user {user_id!s}"
        )
    await db.refresh(updated)
    return _to_domain(updated, user_id=user_id)


async def soft_delete_by_idx(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
    idx: int,
) -> None:
    """Mark the ``(product_id, order_idx)`` row as deleted per §11.D.

    DECISION FLAG §11-IMAGE-D1 — writes ``status='deleted'`` (NOT
    ``deleted_at=NOW()``) because the column does not exist in V1
    schema.

    NOT exposed via any router in V1 per §11.M — internal helper for:

    * the catalog soft-delete cascade (when ``catalog.delete_product``
      soft-deletes a product, this method may be called to flag the
      image rows; V1 leaves them orphaned because ``ON DELETE CASCADE``
      does not fire on a parent soft-delete);
    * the V1.5 re-upload flow (DELETE-image endpoint).
    """
    # Tenancy via products.user_id sub-select — same `scope_to_user`
    # anchor pattern as `update_precheck_result`.
    owned_product_ids = scope_to_user(select(ProductORM.id), user_id)
    stmt = (
        update(ProductImageORM)
        .where(ProductImageORM.product_id == product_id)
        .where(ProductImageORM.order_idx == idx)
        .where(ProductImageORM.product_id.in_(owned_product_ids))
        .values(status="deleted")
    )
    await db.execute(stmt)


# ─────────────────────────────────────────────────────────────────────────────
# Reads
# ─────────────────────────────────────────────────────────────────────────────
async def find_by_product(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
) -> list[ProductImage]:
    """SELECT all non-deleted ``product_images`` rows for ``product_id``
    ordered by ``order_idx`` ASC per §11.D.

    Tenancy via :func:`scope_to_user` on the joined ``Product`` —
    proves the §19 anchor for this table even though it carries no
    direct ``user_id`` column.

    DECISION FLAG §11-IMAGE-D1 — filters ``status != 'deleted'``
    instead of ``deleted_at IS NULL``.
    """
    owned_pid = _owned_product_ids_subquery(user_id, product_id)
    stmt = (
        select(ProductImageORM)
        .where(ProductImageORM.product_id.in_(owned_pid))
        .where(ProductImageORM.status != "deleted")
        .order_by(ProductImageORM.order_idx.asc())
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [_to_domain(row, user_id=user_id) for row in rows]


async def find_by_id(
    db: AsyncSession,
    user_id: UUID,
    image_id: UUID,
) -> ProductImage | None:
    """SELECT a single image by ID, tenant-scoped through ``products``.

    Returns ``None`` for any of:

    * image_id does not exist,
    * image exists but its product is owned by another user,
    * image is soft-deleted (``status='deleted'``).

    All three cases collapse to ``None`` — the service layer translates
    to :class:`ImageNotFoundError` uniformly per §11.H + leak protection.
    """
    # `scope_to_user` anchor against the join target.
    owned_product_ids = scope_to_user(select(ProductORM.id), user_id)
    stmt = (
        select(ProductImageORM)
        .where(ProductImageORM.id == image_id)
        .where(ProductImageORM.product_id.in_(owned_product_ids))
        .where(ProductImageORM.status != "deleted")
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return _to_domain(row, user_id=user_id)


async def find_by_slot(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
    idx: int,
) -> ProductImage | None:
    """SELECT the image occupying ``(product_id, order_idx=idx)`` if any
    per §11.D step 4 (slot uniqueness check).

    Returns the matching row regardless of soft-delete state — the DB
    ``UNIQUE(product_id, order_idx)`` constraint per `MVP_ARCH §2.5`
    means at most one row exists, and we use this method to detect
    occupancy BEFORE attempting INSERT.

    DECISION FLAG §11-IMAGE-D1 — no ``deleted_at`` filter applied;
    soft-deleted rows still occupy the slot under the UNIQUE constraint.
    A V1.5 re-upload flow may need to relax this (partial UNIQUE WHERE
    status != 'deleted'); deferred per §11.M.
    """
    owned_pid = _owned_product_ids_subquery(user_id, product_id)
    stmt = (
        select(ProductImageORM)
        .where(ProductImageORM.product_id.in_(owned_pid))
        .where(ProductImageORM.order_idx == idx)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return _to_domain(row, user_id=user_id)


# ─────────────────────────────────────────────────────────────────────────────
# Aggregations
# ─────────────────────────────────────────────────────────────────────────────
async def summarize_by_products(
    db: AsyncSession,
    user_id: UUID,
    product_ids: list[UUID],
) -> dict[UUID, ImageStatusSummary]:
    """Aggregation query per §11.D — counts by status per product +
    front-image ``gcs_path`` for downstream signed-URL generation.

    Returns an entry for every requested ``product_id`` — products with
    no images get an :class:`ImageStatusSummary` of zeros and
    ``front_image_signed_url=None``.

    NOTE: the dataclass field is ``front_image_signed_url`` but this
    repository returns the GCS PATH (not the signed URL).  The service
    layer (:func:`.service.summary`) calls
    ``adapters.gcs.generate_signed_url`` to convert path → URL.

    The repository returns a partial :class:`ImageStatusSummary` where
    ``front_image_signed_url`` carries the PATH (NOT the URL); the
    service surface re-wraps with the actual signed URL before
    returning to the dashboard caller.
    """
    if not product_ids:
        return {}

    # Tenancy via subquery scope.
    owned_pid = (
        scope_to_user(select(ProductORM.id), user_id)
        .where(ProductORM.id.in_(product_ids))
        .where(ProductORM.deleted_at.is_(None))
    )

    # Per-product per-status counts.
    count_stmt = (
        select(
            ProductImageORM.product_id,
            ProductImageORM.status,
            func.count(ProductImageORM.id).label("n"),
        )
        .where(ProductImageORM.product_id.in_(owned_pid))
        .where(ProductImageORM.status != "deleted")
        .group_by(ProductImageORM.product_id, ProductImageORM.status)
    )
    counts_result = await db.execute(count_stmt)

    # Initialise every requested product to zeros.
    accum: dict[UUID, dict] = {
        pid: {"total": 0, "ready": 0, "failed": 0, "pending": 0, "front_path": None}
        for pid in product_ids
    }

    for pid, status_str, n in counts_result.all():
        if pid not in accum:
            continue
        accum[pid]["total"] += int(n)
        if status_str == "ready":
            accum[pid]["ready"] += int(n)
        elif status_str == "failed_precheck":
            accum[pid]["failed"] += int(n)
        elif status_str == "pending":
            accum[pid]["pending"] += int(n)

    # Front-image paths — order_idx=1, status='ready'.
    front_stmt = (
        select(ProductImageORM.product_id, ProductImageORM.gcs_path)
        .where(ProductImageORM.product_id.in_(owned_pid))
        .where(ProductImageORM.order_idx == 1)
        .where(ProductImageORM.status == "ready")
    )
    front_result = await db.execute(front_stmt)
    for pid, gcs_path in front_result.all():
        if pid in accum:
            accum[pid]["front_path"] = gcs_path

    return {
        pid: ImageStatusSummary(
            product_id=pid,
            total_images=data["total"],
            ready_count=data["ready"],
            failed_count=data["failed"],
            pending_count=data["pending"],
            front_image_signed_url=data["front_path"],  # PATH not URL; service wraps.
        )
        for pid, data in accum.items()
    }


__all__ = [
    "find_by_id",
    "find_by_product",
    "find_by_slot",
    "insert",
    "soft_delete_by_idx",
    "summarize_by_products",
    "update_precheck_result",
]
