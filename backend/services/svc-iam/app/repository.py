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

from app.domain import GoogleUpsertOutcome
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


# ─────────────────────────────────────────────────────────────────────────────
# Google Sign-In identity lookups + upsert (google-auth feature — design §E)
# ─────────────────────────────────────────────────────────────────────────────
async def find_user_by_google_sub(db: AsyncSession, google_sub: str) -> User | None:
    """Locate a user by Google stable subject (``google_sub``).

    Module-private per §7.D — callers outside iam use the service layer.
    """
    result = await db.execute(select(User).where(User.google_sub == google_sub))
    return result.scalar_one_or_none()


async def find_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Locate a user by verified ``email`` (the linking key).

    ``email`` is a nullable-UNIQUE column post-migration c2d3e4f5a6b7, so this
    is a single-row UNIQUE-index lookup.  Module-private per §7.D.
    """
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def upsert_user_on_google_login(
    db: AsyncSession, *, google_sub: str, email: str, ip: str, capture_dpdp: bool
) -> GoogleUpsertOutcome:
    """Insert-or-link on a verified Google login per design §E.2.

    Deterministic linking algorithm (the caller has already verified the token
    AND ``email_verified == true`` in the adapter):

    1. **Match by ``google_sub``** → returning Google user.  UPDATE
       ``last_login_at`` + ``auth_provider='google'``.  (Email is NOT
       overwritten in V1 — edge case 3; if the token email differs from the
       stored email, the caller logs ``auth.google.email_changed``.)
    2. **Else match by verified ``email``** → an existing (phone-OTP) user with
       ``google_sub IS NULL``.  LINK: set ``google_sub``, ``auth_provider=
       'google'``, UPDATE ``last_login_at``.  Login as the existing user
       (preserves catalogs / plan / history).
       * If that user already has a *different* ``google_sub`` → the caller
         raises ``GoogleIdentityConflictError`` (409); this function returns
         the row and signals the conflict via :class:`GoogleUpsertOutcome`.
    3. **Else** → CREATE a Google-only user: ``phone=NULL``, ``email``,
       ``google_sub``, ``auth_provider='google'``, ``plan='free'``,
       ``last_login_at=NOW()``.

    This runs inside the caller's transaction (no commit here — the service /
    ``get_db`` owns the boundary), exactly like ``upsert_user_on_login``.

    Returns:
        :class:`GoogleUpsertOutcome` carrying the (new or updated) ``User``,
        the ``linked`` flag (rule 2 fired), the ``created`` flag (rule 3
        fired), the ``email_changed`` flag (rule 1 with a differing token
        email), and the ``conflict`` flag (rule 2 against a different
        ``google_sub``).
    """
    now = datetime.now(timezone.utc)

    # ── Rule 1: known google_sub → login ───────────────────────────────────
    existing = await find_user_by_google_sub(db, google_sub)
    if existing is not None:
        email_changed = bool(existing.email) and existing.email != email
        existing.last_login_at = now
        existing.auth_provider = "google"
        _maybe_log_dpdp(capture_dpdp, existing, ip, is_insert=False)
        await db.flush()
        await db.refresh(existing)
        return GoogleUpsertOutcome(
            user=existing, linked=False, created=False,
            email_changed=email_changed, conflict=False,
        )

    # ── Rule 2: verified email matches an existing user ────────────────────
    by_email = await find_user_by_email(db, email)
    if by_email is not None:
        if by_email.google_sub is not None and by_email.google_sub != google_sub:
            # Edge case 4 — email belongs to a DIFFERENT Google account.
            # Fail closed; signal to the service to raise 409.
            return GoogleUpsertOutcome(
                user=by_email, linked=False, created=False,
                email_changed=False, conflict=True,
            )
        # Link the Google identity onto the existing (phone) user.
        by_email.google_sub = google_sub
        by_email.auth_provider = "google"
        by_email.last_login_at = now
        _maybe_log_dpdp(capture_dpdp, by_email, ip, is_insert=False)
        await db.flush()
        await db.refresh(by_email)
        return GoogleUpsertOutcome(
            user=by_email, linked=True, created=False,
            email_changed=False, conflict=False,
        )

    # ── Rule 3: no match → create a Google-only user ───────────────────────
    user = User(
        phone=None,
        email=email,
        google_sub=google_sub,
        auth_provider="google",
        plan="free",
        last_login_at=now,
    )
    db.add(user)
    _maybe_log_dpdp(capture_dpdp, user, ip, is_insert=True)
    await db.flush()
    await db.refresh(user)
    return GoogleUpsertOutcome(
        user=user, linked=False, created=True,
        email_changed=False, conflict=False,
    )


def _maybe_log_dpdp(capture_dpdp: bool, user: User, ip: str, *, is_insert: bool) -> None:
    """DPDP-consent parity with the OTP path (design §F.4).

    V1 GAP — the ``dpdp_consented_at`` column does not exist (a pre-existing,
    separately-owned V1.5 hand-off).  The Google path inherits the SAME
    no-op-with-warning behaviour as ``upsert_user_on_login`` so neither
    provider is special-cased.  Do NOT add the column inside this feature.
    """
    if capture_dpdp and not hasattr(user, "dpdp_consented_at"):
        logger.info(
            "dpdp_consent.skipped_no_column provider=google ip=%s is_insert=%s",
            ip,
            is_insert,
        )


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
    "find_user_by_google_sub",
    "find_user_by_email",
    "upsert_user_on_google_login",
]
