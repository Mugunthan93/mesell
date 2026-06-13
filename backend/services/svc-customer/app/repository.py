"""``customer`` repository — module-private SQLAlchemy 2.0 typed CRUD over
``seller_profile``.

Per BACKEND_ARCHITECTURE.md §8.D (LOCKED 2026-06-05).

Module-private rule (§16)
-------------------------
These functions are NOT importable by other modules.  Cross-module code
that needs profile info MUST call :func:`app.modules.customer.service.get_profile`
(or one of the other public service surfaces) — NEVER
``from app.modules.customer.repository import find_by_user_id``.  The §19
import-linter contract pins this.

Tenancy (§4.C — locked)
-----------------------
``seller_profile.user_id`` is BOTH primary key AND the tenancy column.
**Every method** in this repository passes through
:func:`app.core.tenancy.scope_to_user` even though the PK lookup alone
would already isolate the tenant — the ``scope_to_user`` invocation is
the §19 grep-anchor that proves the tenancy invariant holds.

Writes load the row via a ``scope_to_user``-wrapped SELECT first, then
mutate the loaded ORM instance and ``flush`` — this keeps both the
SELECT (tenancy-scoped) and the WRITE (PK-scoped via SQLAlchemy's
identity map) safe in a single readable path.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import scope_to_user
from app.shared.models.seller_profile import SellerProfile as SellerProfileORM

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Allowlist of column names the repository will accept in ``upsert``.
# ─────────────────────────────────────────────────────────────────────────────
# Defensive: prevents a caller passing ``user_id``, ``onboarding_complete``,
# ``active_super_categories``, or ``compliance_extensions`` inside the
# ``fields`` dict and side-stepping the service-layer recompute.  The other
# columns have dedicated repository methods.
_BASE_FIELD_ALLOWLIST: frozenset[str] = frozenset({
    "manufacturer_name",
    "manufacturer_address",
    "manufacturer_pincode",
    "packer_name",
    "packer_address",
    "packer_pincode",
    "importer_name",
    "importer_address",
    "importer_pincode",
    "country_of_origin",
})


async def find_by_user_id(
    db: AsyncSession, user_id: UUID
) -> SellerProfileORM | None:
    """Locate a seller profile by ``user_id``.

    Returns ``None`` if no row exists (first-time seller).  Module-private
    per §8.D — callers outside ``customer`` MUST use the service layer.

    Tenancy: ``scope_to_user`` adds ``WHERE user_id = :user_id`` even
    though it is also the PK.  This is the §19 grep anchor.
    """
    stmt = scope_to_user(select(SellerProfileORM), user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def upsert(
    db: AsyncSession,
    user_id: UUID,
    fields: dict[str, Any],
    *,
    onboarding_complete: bool,
) -> SellerProfileORM:
    """Insert-or-update the seller profile per the first-PATCH-creates-row
    pattern (§8.B.2).

    Behaviour:

    - On first PATCH (no row) the caller provides ENOUGH fields to satisfy
      the ORM's NOT NULL constraints on the 6 mandatory base fields.  If
      not, asyncpg / SQLAlchemy raises an IntegrityError and the service
      surfaces it as 422.
    - On subsequent PATCH the existing row is updated with only the
      provided fields (subset semantics — absent fields untouched).

    ``onboarding_complete`` is ALWAYS computed by the service and passed
    here; the repository never recomputes it.  The repository never
    commits — the FastAPI ``get_db`` dependency owns commit/rollback.

    Tenancy: read goes through :func:`scope_to_user`; the write uses
    SQLAlchemy's identity map (the row instance loaded above carries
    ``user_id`` in its PK column).
    """
    # Drop any caller-supplied disallowed keys to guarantee the recompute
    # invariant.  Logged at WARNING so developer drift surfaces in CI.
    sanitised: dict[str, Any] = {}
    for key, value in fields.items():
        if key in _BASE_FIELD_ALLOWLIST:
            sanitised[key] = value
        else:
            logger.warning(
                "customer.repo.upsert: dropping disallowed field %r (callers must "
                "use update_active_categories / update_compliance_extension instead)",
                key,
            )

    # Tenancy-scoped read of the existing row.  Inline (rather than
    # delegating to find_by_user_id) so the §19 grep anchor
    # ``scope_to_user(`` appears at the call site of every repository
    # mutator.
    stmt = scope_to_user(select(SellerProfileORM), user_id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if existing is None:
        # First PATCH — INSERT a brand-new row.
        row = SellerProfileORM(
            user_id=user_id,
            onboarding_complete=onboarding_complete,
            created_at=now,
            updated_at=now,
            **sanitised,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return row

    # Update path — only assign the provided fields, never overwrite untouched
    # fields with None.
    for key, value in sanitised.items():
        setattr(existing, key, value)
    existing.onboarding_complete = onboarding_complete
    existing.updated_at = now
    await db.flush()
    await db.refresh(existing)
    return existing


async def update_active_categories(
    db: AsyncSession,
    user_id: UUID,
    super_ids: list[str],
    *,
    onboarding_complete: bool,
) -> SellerProfileORM:
    """Replace ``active_super_categories`` entirely per §8.B.3.

    Raises:
        ValueError: when no row exists.  The service-layer asserts profile
            existence upstream (this endpoint requires base fields to be
            present first, per the wizard flow).

    Tenancy: read goes through :func:`scope_to_user`; the write mutates
    the loaded ORM instance.
    """
    stmt = scope_to_user(select(SellerProfileORM), user_id)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        raise ValueError(
            f"customer.repo.update_active_categories: no row for user_id={user_id}"
        )
    row.active_super_categories = list(super_ids)
    row.onboarding_complete = onboarding_complete
    row.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(row)
    return row


async def update_compliance_extension(
    db: AsyncSession,
    user_id: UUID,
    super_id: str,
    payload: dict[str, Any],
    *,
    onboarding_complete: bool,
) -> SellerProfileORM:
    """JSONB-merge update at the ``{super_id}`` key in ``compliance_extensions``.

    Does NOT affect other ``super_id`` entries — the merge happens
    Python-side because Postgres' ``jsonb_set`` requires the parent path
    to exist when ``create_missing=false``, and nested-merge semantics
    are easier to keep right at the Python layer for V1 volumes (one
    seller's compliance dict is tiny — sub-1KB).

    Raises:
        ValueError: when no row exists.

    Tenancy: read goes through :func:`scope_to_user`.
    """
    stmt = scope_to_user(select(SellerProfileORM), user_id)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        raise ValueError(
            f"customer.repo.update_compliance_extension: no row for user_id={user_id}"
        )

    # Reassign (not in-place mutate) so SQLAlchemy detects the change on
    # the JSONB column.
    current: dict[str, dict[str, Any]] = dict(row.compliance_extensions or {})
    merged_super = dict(current.get(super_id, {}))
    merged_super.update(payload)
    current[super_id] = merged_super
    row.compliance_extensions = current
    row.onboarding_complete = onboarding_complete
    row.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(row)
    return row


__all__ = [
    "find_by_user_id",
    "update_active_categories",
    "update_compliance_extension",
    "upsert",
]
