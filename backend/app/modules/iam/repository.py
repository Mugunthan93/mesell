"""``iam`` repository — module-private SQLAlchemy 2.0 typed CRUD over ``users``.

Per BACKEND_ARCHITECTURE.md §7.D (LOCKED 2026-06-05).

Module-private rule (§16)
-------------------------
These functions are NOT importable by other modules.  Cross-module code that
needs user info MUST call :func:`app.modules.iam.service.get_profile` —
NEVER ``from app.modules.iam.repository import find_user_by_phone``.  The
§19 import-linter contract pins this.

Tenancy
-------
``users`` is itself the scoping subject (per §7.I), so ``core/tenancy.scope_to_user``
is NOT used here.  The principal IS the row.

DPDP capture — V1 GAP
---------------------
§7.B.2 flow specifies::

    SET dpdp_consented_at = now() if currently NULL

But the live schema (``app/shared/models/user.py``) DOES NOT carry a
``dpdp_consented_at`` column.  ``MVP_ARCHITECTURE.md §2.1`` does not declare
it; no Alembic migration adds it.  The §7.B.2 promise cannot be honoured
without a schema change owned by ``meesell-database-builder``.

Resolution path (flagged for master): the ``capture_dpdp: bool`` parameter is
preserved on the locked signature, but the column-write is a no-op + WARNING
log.  Adding the column is a §V1.5 hand-off — or escalates to a §7.5
amendment.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.user import User

logger = logging.getLogger(__name__)


async def find_user_by_phone(db: AsyncSession, phone: str) -> User | None:
    """Locate a user by E.164 phone.  Returns ``None`` if absent.

    Per §7.D — module-private; callers outside iam MUST use the service layer.
    """
    result = await db.execute(select(User).where(User.phone == phone))
    return result.scalar_one_or_none()


async def upsert_user_on_login(
    db: AsyncSession, phone: str, ip: str, capture_dpdp: bool
) -> User:
    """Insert-or-update on successful OTP verify per §7.B.2 flow step 2.

    Semantics:

    * If no row for ``phone``: INSERT a new ``users`` row with plan ``"free"``,
      ``last_login_at = NOW()``.
    * If a row exists: UPDATE ``last_login_at = NOW()``.
    * If ``capture_dpdp`` AND the column existed: SET ``dpdp_consented_at = NOW()``
      when currently NULL.  **V1 GAP** — column missing; logged + no-op.

    Args:
        db: Caller's async session.  The repository does NOT commit — the
            service layer owns transaction boundary.
        phone: E.164 string.  The caller has already Pydantic-validated.
        ip: Client IP captured for audit purposes.  Not currently persisted
            on ``users`` (no column); audit middleware row captures it.
        capture_dpdp: True on every verify path per CLAUDE.md Decision 14
            DPDP rule.  V1 no-op due to missing column — see module docstring.

    Returns:
        The (new or updated) :class:`User` ORM instance, refreshed.
    """
    user = await find_user_by_phone(db, phone)
    now = datetime.now(timezone.utc)
    is_insert = user is None
    if is_insert:
        user = User(phone=phone, plan="free", last_login_at=now)
        db.add(user)
    else:
        user.last_login_at = now

    if capture_dpdp and not hasattr(user, "dpdp_consented_at"):
        # V1 schema gap — column does not exist on the User model.
        # Logged once per call to make the gap observable; no-op on the row.
        logger.info(
            "dpdp_consent.skipped_no_column user_phone_present=%s ip=%s is_insert=%s",
            bool(phone),
            ip,
            is_insert,
        )

    await db.flush()  # populate user.id without committing — service owns the txn
    await db.refresh(user)
    return user


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    """Fetch a user row by primary key.

    Used by:

    * ``service.get_profile`` to back ``GET /api/v1/auth/me``.
    * ``service.rotate_refresh_token`` to re-read the ``plan`` claim on
      refresh (V1 always ``"free"``; reserved for V1.5 plan transitions).
    """
    return await db.get(User, user_id)


async def update_plan(db: AsyncSession, user_id: UUID, plan: str) -> None:
    """V1.5 — Razorpay subscription state → ``users.plan``.

    Per §7.D this is reserved for V1.5 when subscription business logic
    lands.  V1 callers do not invoke it; the method body is implemented as
    a no-op-friendly update for forward compatibility.
    """
    user = await db.get(User, user_id)
    if user is None:
        return
    user.plan = plan
    await db.flush()


__all__ = [
    "find_user_by_phone",
    "upsert_user_on_login",
    "get_user_by_id",
    "update_plan",
]
