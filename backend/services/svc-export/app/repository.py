"""``export`` repository — MODULE-PRIVATE SQLAlchemy queries per §14.D.

Vendored from the monolith ``app.modules.export.repository``.  Bound to the
``export`` Postgres schema (the vendored ``app.shared.models.export.Export``
ORM carries ``__table_args__ = {"schema": "export"}``).  The ONLY import-line
changes from the monolith are the intra-tree path rewrites:

* ``from app.modules.export.domain import Export, ExportStatusSummary``
  → ``from app.domain import Export, ExportStatusSummary``

``app.core.tenancy.scope_to_user`` and ``app.shared.models.export.Export`` are
at the same flat paths in the svc-export tree, so those imports are unchanged.
Every executable line below is byte-for-byte from the monolith repository.

DDL gap reconciliation — DECISION FLAGS (unchanged from monolith)
=================================================================
D1 — ``initiated_at`` ← ``created_at``; ``completed_at`` not persisted.
D2 — ``format`` field NOT persisted (derived from ``zip_gcs_path`` / Valkey hint).
D3 — ``error_code`` prefix in ``error_message`` (``"[code] message"``).
D4 — ``round_trip_validated`` implied TRUE on ``status='ready'``.
D5 — explicit ``status='pending'`` on insert (override the ``'processing'`` default).
D6 — ``download_url`` column is vestigial.
See the monolith repository docstring for full prose.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import scope_to_user
from app.domain import Export, ExportStatusSummary
from app.shared.models.export import Export as ExportORM

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _format_from_paths(zip_gcs_path: str | None) -> Literal[
    "xlsx_only", "xlsx_with_images"
]:
    """Derive ``format`` from ``zip_gcs_path`` per D2."""
    return "xlsx_with_images" if zip_gcs_path else "xlsx_only"


def _parse_error_code(error_message: str | None) -> tuple[str | None, str | None]:
    """Parse the ``"[code] message"`` prefix per D3.

    Returns ``(error_code, plain_error_message)``.  No bracketed prefix →
    ``(None, error_message)``.
    """
    if not error_message:
        return None, error_message
    if not error_message.startswith("["):
        return None, error_message
    close_idx = error_message.find("]")
    if close_idx < 2:
        return None, error_message
    code = error_message[1:close_idx].strip()
    if not code:
        return None, error_message
    rest = error_message[close_idx + 1 :]
    if rest.startswith(" "):
        rest = rest[1:]
    return code, rest


def _orm_to_domain(
    row: ExportORM,
    *,
    pending_format_hint: Literal["xlsx_only", "xlsx_with_images"] | None = None,
) -> Export:
    """Convert an ORM row → frozen :class:`Export` domain instance (D1-D4)."""
    error_code, plain_error_message = _parse_error_code(row.error_message)
    status_val = row.status if row.status in ("pending", "ready", "failed") else "pending"
    if status_val == "pending" and pending_format_hint is not None:
        fmt: Literal["xlsx_only", "xlsx_with_images"] = pending_format_hint
    else:
        fmt = _format_from_paths(row.zip_gcs_path)
    return Export(
        id=row.id,
        user_id=row.user_id,
        product_id=row.product_id,
        format=fmt,
        status=status_val,  # type: ignore[arg-type]
        xlsx_gcs_path=row.xlsx_gcs_path,
        zip_gcs_path=row.zip_gcs_path,
        error_message=plain_error_message,
        error_code=error_code,
        round_trip_validated=True if status_val == "ready" else None,
        initiated_at=row.created_at,
        completed_at=None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Writes
# ─────────────────────────────────────────────────────────────────────────────
async def insert(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
    format: Literal["xlsx_only", "xlsx_with_images"],  # noqa: A002 — API contract
    initiated_at: datetime,
) -> Export:
    """INSERT a new ``exports`` row with ``status='pending'`` (D5)."""
    del format, initiated_at  # consumed by service layer + DDL server_default

    row = ExportORM(
        user_id=user_id,
        product_id=product_id,
        status="pending",  # D5 — explicit override of 'processing' server_default
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return _orm_to_domain(row)


async def find_by_id(
    db: AsyncSession,
    user_id: UUID,
    export_id: UUID,
    *,
    pending_format_hint: Literal["xlsx_only", "xlsx_with_images"] | None = None,
) -> Export | None:
    """Find an export by ID, tenant-scoped per §4.C.

    Returns ``None`` if not found OR not owned by ``user_id`` (404 conflation).
    """
    stmt = scope_to_user(select(ExportORM), user_id).where(ExportORM.id == export_id)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return _orm_to_domain(row, pending_format_hint=pending_format_hint)


async def update_status_ready(
    db: AsyncSession,
    user_id: UUID,
    export_id: UUID,
    xlsx_gcs_path: str,
    zip_gcs_path: str | None,
    completed_at: datetime,
    round_trip_validated: bool,
) -> Export:
    """Worker-only — update the exports row from ``'pending'`` to ``'ready'``."""
    del completed_at, round_trip_validated  # D1 + D4 — not persisted at SQL.

    owned_export_ids = scope_to_user(select(ExportORM.id), user_id)
    stmt = (
        update(ExportORM)
        .where(ExportORM.id == export_id)
        .where(ExportORM.id.in_(owned_export_ids))
        .values(
            status="ready",
            xlsx_gcs_path=xlsx_gcs_path,
            zip_gcs_path=zip_gcs_path,
        )
        .returning(ExportORM)
    )
    result = await db.execute(stmt)
    updated = result.scalar_one_or_none()
    if updated is None:
        raise LookupError(
            f"update_status_ready: export {export_id!s} not found "
            f"under user {user_id!s}"
        )
    await db.refresh(updated)
    return _orm_to_domain(updated)


async def update_status_failed(
    db: AsyncSession,
    user_id: UUID,
    export_id: UUID,
    error_message: str,
    error_code: str,
    completed_at: datetime,
) -> Export:
    """Worker-only — update the exports row from ``'pending'`` to ``'failed'`` (D3)."""
    del completed_at  # D1 — not a DDL column.

    safe_code = error_code.replace("]", "").strip() or "unknown"
    composed = f"[{safe_code}] {error_message}"

    owned_export_ids = scope_to_user(select(ExportORM.id), user_id)
    stmt = (
        update(ExportORM)
        .where(ExportORM.id == export_id)
        .where(ExportORM.id.in_(owned_export_ids))
        .values(
            status="failed",
            error_message=composed,
        )
        .returning(ExportORM)
    )
    result = await db.execute(stmt)
    updated = result.scalar_one_or_none()
    if updated is None:
        raise LookupError(
            f"update_status_failed: export {export_id!s} not found "
            f"under user {user_id!s}"
        )
    await db.refresh(updated)
    return _orm_to_domain(updated)


# ─────────────────────────────────────────────────────────────────────────────
# Aggregations (OPTIONAL — V1.5 dashboard elevation per §2.D matrix)
# ─────────────────────────────────────────────────────────────────────────────
async def summarize_by_products(
    db: AsyncSession,
    user_id: UUID,
    product_ids: list[UUID],
) -> dict[UUID, ExportStatusSummary]:
    """Return the latest export row per ``product_id``.  OPTIONAL surface."""
    if not product_ids:
        return {}

    result_map: dict[UUID, ExportStatusSummary] = {
        pid: ExportStatusSummary(
            product_id=pid,
            latest_export_id=None,
            latest_export_status=None,
            latest_completed_at=None,
        )
        for pid in product_ids
    }
    for pid in product_ids:
        stmt = (
            scope_to_user(select(ExportORM), user_id)
            .where(ExportORM.product_id == pid)
            .order_by(ExportORM.created_at.desc())
            .limit(1)
        )
        res = await db.execute(stmt)
        row = res.scalar_one_or_none()
        if row is None:
            continue
        status_val = row.status if row.status in ("pending", "ready", "failed") else "pending"
        result_map[pid] = ExportStatusSummary(
            product_id=pid,
            latest_export_id=row.id,
            latest_export_status=status_val,  # type: ignore[arg-type]
            latest_completed_at=None,  # D1 — not persisted
        )
    return result_map


__all__ = [
    "find_by_id",
    "insert",
    "summarize_by_products",
    "update_status_failed",
    "update_status_ready",
]
