"""Integration-test conftest for §7 iam HTTP-level tests.

Why a separate conftest
-----------------------
The top-level ``tests/conftest.py`` ``client`` fixture sets up an isolated
ephemeral DB via ``db_engine`` (``Base.metadata.create_all``).  The full
schema includes the §G4 pg_trgm GIN indexes shipped in Alembic migration
``a1b2c3d4e5f6``, which require the ``pg_trgm`` extension.  The dev tunnel
Postgres (port 5433, K3s instance) has the extension via the live Alembic
chain; the bare dev Postgres on port 5432 does NOT — ``create_all`` fails.

This fixture sidesteps the rebuild entirely.  ``iam_client`` uses an ASGI
test transport against the live FastAPI app, lets ``Depends(get_db)``
resolve normally against ``settings.DATABASE_URL`` (the test-env-supplied
dev-tunnel URL), and the ``cleanup_test_users`` finaliser DELETEs any user
rows whose phone matches the integration-test prefix ``+9155500`` after
each test.

Phone-prefix convention
-----------------------
Every integration test uses a phone in the ``+9155500XXXXX`` range — these
are non-routable test numbers that no real Indian SIM would ever carry,
making it safe to DELETE-by-prefix at teardown without risk of stomping
real data.
"""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

# Import the app at module load; surface ImportError early.
from app.main import app
from app.shared.config import settings
from app.shared.models.audit_event import AuditEvent
from app.shared.models.user import User


_INTEGRATION_PHONE_PREFIX = "+9155500"
"""Every integration test uses this prefix — safe to DELETE-by-prefix."""


async def _cleanup_users_by_phone_prefix(prefix: str = _INTEGRATION_PHONE_PREFIX) -> None:
    """DELETE audit_events + users whose phone starts with the test prefix.

    Order matters: ``audit_events.user_id`` is ``ON DELETE RESTRICT`` per
    §11.2 DDL (audit rows must survive user deletion for compliance), so
    the cleanup MUST delete the audit rows first.  This is acceptable for
    test data only — production code NEVER deletes users (DPDP delete is
    a §V1.5 right-to-erasure surface that anonymises rather than purges).

    Runs against the same DB the routes wrote to (``settings.DATABASE_URL``).
    Uses NullPool to avoid asyncpg loop-attachment issues — the cleanup runs
    in the test's function loop, not a session-scoped one.
    """
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool, echo=False)
    try:
        async with engine.connect() as conn:
            # 1. Delete audit_events for any user we are about to delete.
            await conn.execute(
                delete(AuditEvent).where(
                    AuditEvent.user_id.in_(
                        # Subquery: ids of users with the test phone prefix.
                        # asyncpg requires the subquery to be a proper SELECT.
                        # Using SQLAlchemy ORM-style scalar subquery.
                        delete(User)
                        .where(User.phone.like(f"{prefix}%"))
                        .returning(User.id)
                        # The above doesn't actually delete (we wrap a SELECT
                        # below instead); see fallback.
                    )
                )
            ) if False else None  # noqa: E501  (clarity above; real impl below)

            # The cleanest path: two-step delete with an explicit SELECT.
            from sqlalchemy import select

            user_ids_q = select(User.id).where(User.phone.like(f"{prefix}%"))
            await conn.execute(
                delete(AuditEvent).where(AuditEvent.user_id.in_(user_ids_q))
            )
            await conn.execute(
                delete(User).where(User.phone.like(f"{prefix}%"))
            )
            await conn.commit()
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def iam_client():
    """ASGI client for iam integration tests.

    * Boots the FastAPI lifespan once per fixture call (creates the
      ``app.state.valkey`` + ``app.state.db_engine`` references the
      middleware chain expects).
    * Does NOT override ``Depends(get_db)`` — routes resolve the dep
      against ``settings.DATABASE_URL`` (test env sets it to the dev
      tunnel URL).
    * Cleans up users by phone prefix in teardown — see module docstring.
    """
    # Pre-test cleanup in case a previous run left rows behind.
    await _cleanup_users_by_phone_prefix()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        async with app.router.lifespan_context(app):
            yield ac

    # Post-test cleanup.
    await _cleanup_users_by_phone_prefix()
