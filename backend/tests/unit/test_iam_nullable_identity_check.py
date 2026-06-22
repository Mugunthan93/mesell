"""OB-BE-25 — nullable-identity CHECK constraint test.

Directly asserts the DB-level invariant:
    ``phone IS NOT NULL OR google_sub IS NOT NULL``   (ck_users_at_least_one_identity)

Attempts to INSERT a user row with BOTH phone=NULL AND google_sub=NULL must be
rejected by PostgreSQL with an IntegrityError (CheckViolation).

This test uses the ``db_session`` → aliased ``db`` fixture from the customer
module conftest pattern (ephemeral test DB, NullPool, per-test ROLLBACK).

Decision lock:
- This is a DB-level assertion — NOT an API call.  The guard lives in the
  migration and the ORM model ``__table_args__`` CheckConstraint.
- We must NOT edit the User model to pass this test; if the constraint is
  absent from the current schema, the test fails loudly as a defect signal.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.asyncio


async def test_nullable_identity_check_rejects_both_null(db_session):
    """OB-BE-25: INSERT a user with phone=NULL AND google_sub=NULL → IntegrityError.

    Arrange: raw SQL INSERT with both identity columns NULL (the schema CHECK guard).
    Act: flush/execute.
    Assert: IntegrityError is raised (PostgreSQL CHECK constraint violation).
    """
    # Use raw SQL to bypass any ORM-level defaults that might fill in values.
    stmt = text(
        "INSERT INTO users (id, phone, google_sub, plan, created_at) "
        "VALUES (:id, NULL, NULL, 'free', NOW())"
    )
    with pytest.raises(IntegrityError, match="ck_users_at_least_one_identity"):
        await db_session.execute(stmt, {"id": str(uuid.uuid4())})
        await db_session.flush()


async def test_nullable_identity_check_allows_phone_only(db_session):
    """OB-BE-25 (positive): phone IS NOT NULL + google_sub=NULL is valid.

    The dual-identity invariant requires AT LEAST ONE identity — phone alone satisfies it.
    """
    phone = f"+91999{uuid.uuid4().int % 10000000:07d}"
    stmt = text(
        "INSERT INTO users (id, phone, google_sub, auth_provider, plan, created_at) "
        "VALUES (:id, :phone, NULL, 'phone', 'free', NOW())"
    )
    # Should NOT raise.
    await db_session.execute(stmt, {"id": str(uuid.uuid4()), "phone": phone})
    await db_session.flush()  # constraint check fires here
    # If we reach this line, the constraint is satisfied — that is the assertion.
    assert True


async def test_nullable_identity_check_allows_google_sub_only(db_session):
    """OB-BE-25 (positive): phone=NULL + google_sub IS NOT NULL is valid (Google-only user)."""
    google_sub = f"g-sub-check-{uuid.uuid4().hex[:12]}"
    stmt = text(
        "INSERT INTO users (id, phone, google_sub, auth_provider, plan, created_at) "
        "VALUES (:id, NULL, :google_sub, 'google', 'free', NOW())"
    )
    await db_session.execute(stmt, {"id": str(uuid.uuid4()), "google_sub": google_sub})
    await db_session.flush()
    assert True
