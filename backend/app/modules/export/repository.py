"""``export`` repository — MODULE-PRIVATE SQLAlchemy queries per §14.D.

Per BACKEND_ARCHITECTURE.md §14.D (LOCKED 2026-06-05).

These methods are NOT importable from other modules per §16 boundary —
every cross-module read of ``exports`` data goes through
:mod:`.service` (the optional ``summary`` cross-module surface).

Tenancy
-------
Every method body invokes :func:`app.core.tenancy.scope_to_user` against
the :class:`ExportORM` entity — ``exports.user_id`` is the tenancy
column (explicit per the DDL).  The :func:`scope_to_user` call is the
§19 grep-anchor proving the tenancy invariant.

DDL gap reconciliation — DECISION FLAGS
=======================================

D1 — ``initiated_at`` ← ``created_at``; ``completed_at`` not persisted
----------------------------------------------------------------------
The ``exports`` DDL ships with only ``created_at`` (no ``initiated_at``,
no ``completed_at``, no ``updated_at`` columns).  Mapping:

* API ``initiated_at`` ← DDL ``created_at`` (read-time alias).
* API ``completed_at`` is NOT persisted — always returned as ``None``
  by the API layer.

The ``update_status_ready`` / ``update_status_failed`` methods accept
``completed_at`` parameters for forward-compat (V1.5 migration may add
the column); at the SQL level the value is dropped.

D2 — ``format`` field NOT persisted to DDL
------------------------------------------
The DDL has no ``format`` column.  RESOLUTION:

* The Celery task carries ``format`` in its payload (the pipeline needs
  it to decide whether to produce the ZIP).
* The API GET response derives ``format`` at read-time from
  ``zip_gcs_path``: ``zip_gcs_path IS NOT NULL`` → ``"xlsx_with_images"``;
  ``zip_gcs_path IS NULL`` → ``"xlsx_only"``.
* For ``pending`` rows (no GCS paths yet), the format hint is stored in
  Valkey DB 0 under key ``export:format:{export_id}`` (10-min TTL —
  purely cosmetic for the brief pending window).  Service-layer
  responsibility, not repository.

D3 — ``error_code`` prefix in ``error_message``
-----------------------------------------------
The DDL has no ``error_code`` column.  RESOLUTION:
``update_status_failed`` concatenates ``f"[{error_code}] {error_message}"``
into the existing ``error_message`` column.  The API GET parses the
bracketed prefix back into ``error_code`` at the service layer.

D4 — ``round_trip_validated`` implied TRUE on ``status='ready'``
----------------------------------------------------------------
The DDL has no boolean column.  Per `MVP_ARCH §5.7` contract, the
``status='ready'`` invariant requires round-trip to have passed
(otherwise the pipeline raises :class:`RoundTripValidationError` and
status flips to ``'failed'``).  The API layer returns
``round_trip_validated=True`` whenever ``status='ready'``, ``None``
otherwise.

D5 — explicit ``status='pending'`` on insert
--------------------------------------------
The DDL ``status`` server_default is ``'processing'``, but §14 uses
``'pending'``.  :func:`insert` MUST pass ``status='pending'`` explicitly
to override the server_default.  Status transitions: ``pending →
ready`` OR ``pending → failed``.  The legacy ``'processing'`` is never
written by this module.

D6 — ``download_url`` column is vestigial
-----------------------------------------
The DDL ships a ``download_url TEXT`` column that §14.B.2 does NOT use
(signed URLs are generated fresh per response per §6.D).  This module
leaves the column NULL; never reads from it.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import scope_to_user
from app.modules.export.domain import Export, ExportStatusSummary
from app.shared.models.export import Export as ExportORM

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _format_from_paths(zip_gcs_path: str | None) -> Literal[
    "xlsx_only", "xlsx_with_images"
]:
    """Derive ``format`` from ``zip_gcs_path`` per D2.

    ``zip_gcs_path IS NOT NULL`` → ``"xlsx_with_images"``; else
    ``"xlsx_only"``.  For ``pending`` rows (no GCS paths yet) the
    service layer overrides with the Valkey hint key value before
    composing the API response.
    """
    return "xlsx_with_images" if zip_gcs_path else "xlsx_only"


def _parse_error_code(error_message: str | None) -> tuple[str | None, str | None]:
    """Parse the ``"[code] message"`` prefix per D3.

    Returns ``(error_code, plain_error_message)``.  If no bracketed
    prefix is present, ``(None, error_message)`` is returned.  Defensive
    against malformed prefixes (treats unparseable prefixes as plain
    messages with no code).
    """
    if not error_message:
        return None, error_message
    if not error_message.startswith("["):
        return None, error_message
    close_idx = error_message.find("]")
    if close_idx < 2:
        # No closing bracket OR empty code → treat as plain message.
        return None, error_message
    code = error_message[1:close_idx].strip()
    if not code:
        return None, error_message
    # Strip a single leading space after the closing bracket.
    rest = error_message[close_idx + 1 :]
    if rest.startswith(" "):
        rest = rest[1:]
    return code, rest


def _orm_to_domain(
    row: ExportORM,
    *,
    pending_format_hint: Literal["xlsx_only", "xlsx_with_images"] | None = None,
) -> Export:
    """Convert an ORM row → frozen :class:`Export` domain instance.

    Applies the D1-D4 derivations:

    * ``initiated_at`` ← ``row.created_at`` (D1).
    * ``completed_at`` ← ``None`` always (D1 — not persisted).
    * ``format`` ← derived from ``zip_gcs_path`` for ``ready``/``failed``
      rows; for ``pending`` rows the caller passes
      ``pending_format_hint`` if available (D2).
    * ``error_code`` ← parsed from ``error_message`` prefix (D3).
    * ``round_trip_validated`` ← ``True`` iff ``status='ready'`` (D4).
    """
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
    """INSERT a new ``exports`` row with ``status='pending'``.

    Pre-conditions enforced UPSTREAM by the service caller:

    * :func:`catalog.service.assert_product_ownership` — raised 404 if
      the seller does not own the product;
    * product status == ``'ready'`` per §14.B.1 step 2;
    * front-image present when ``format='xlsx_with_images'`` per
      §14.B.1 step 3.

    Per §14-EXPORT-D5, this method passes ``status='pending'``
    explicitly to override the DDL server_default of ``'processing'``.

    Per §14-EXPORT-D2, the ``format`` parameter is consumed by the
    service-layer Valkey hint key write (``export:format:{export_id}``);
    the repository does NOT persist it to a column.

    Per §14-EXPORT-D1, ``initiated_at`` is mapped to the ORM's
    ``created_at`` field (the only timestamp column on the DDL).  The
    parameter exists to preserve the §14.D signature for forward-compat
    when the migration adds the dedicated column.
    """
    # Note: ``format`` + ``initiated_at`` are accepted to honor the
    # §14.D signature but are NOT persisted as columns per D1+D2.  The
    # service layer wires the Valkey hint + uses ``created_at`` as the
    # API ``initiated_at`` echo via ``_orm_to_domain``.
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

    Returns ``None`` if not found OR not owned by ``user_id`` (404
    conflation per §4.C privacy posture).

    ``pending_format_hint`` is supplied by the service layer when the
    Valkey hint key is present — purely cosmetic for the ``pending``
    window per D2.
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
    """Worker-only — update the exports row from ``'pending'`` to
    ``'ready'`` on pipeline success.

    Writes the 2 GCS paths + ``status='ready'``.  Per D1+D4 the
    ``completed_at`` and ``round_trip_validated`` parameters are
    consumed at the API layer (the timestamp is not a DDL column; the
    validated flag is derived from ``status='ready'``).  The parameters
    are kept for forward-compat with the §14.D signature.

    Tenant-scoped via :func:`scope_to_user`.
    """
    # D1 + D4 — parameters honored by signature; not persisted at SQL.
    del completed_at, round_trip_validated

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
    """Worker-only — update the exports row from ``'pending'`` to
    ``'failed'``.

    Per §14-EXPORT-D3 concatenates ``f"[{error_code}] {error_message}"``
    into the existing ``error_message`` column.  The API GET parses the
    prefix back into ``error_code``.

    Per §14-EXPORT-D1, ``completed_at`` is honored by signature only
    (not persisted).

    Partial GCS uploads are NOT cleaned up in V1 (V1.5 cleanup pass per
    §14.L).
    """
    del completed_at  # D1 — not a DDL column.

    # Defensive — never let a stray ``]`` in the code break round-trip parsing.
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
    """Return the latest export row per ``product_id``.

    Used by :func:`service.summary` — OPTIONAL surface for V1.5
    dashboard elevation per §2.D matrix note.  Dashboard does NOT call
    this in V1 (matrix kept at 8 ✓).

    Implementation: per-product ORDER BY created_at DESC LIMIT 1.  No
    DISTINCT ON because the test DB may or may not be Postgres in some
    CI configurations; we batch with a simple per-product loop here for
    portability.  Production lateral-join optimisation deferred to
    V1.5 when this surface is actually consumed.
    """
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
