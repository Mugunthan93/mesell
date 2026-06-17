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
test transport against the live FastAPI app, and overrides ``Depends(get_db)``
with a function-loop NullPool engine so that route handlers and middleware
never touch the app-global ``AsyncSessionLocal`` (which is bound to the
session loop and would raise ``got Future attached to a different loop``
under pytest-asyncio 0.24 with ``asyncio_default_fixture_loop_scope=session``).

Phone-prefix convention
-----------------------
Every integration test uses a phone in the ``+9155500XXXXX`` range — these
are non-routable test numbers that no real Indian SIM would ever carry,
making it safe to DELETE-by-prefix at teardown without risk of stomping
real data.

Gate-4 cross-loop fix (repair 1)
---------------------------------
Root cause (post-PR-#150 regression): the original ``iam_client`` did NOT
override ``Depends(get_db)``.  Routes therefore resolved the dep against the
app-global ``AsyncSessionLocal`` / engine — a module-import-time singleton
whose asyncpg pool binds connections to whatever loop first touched it (the
*session* loop, via the session-scoped ``_provision_test_schema`` fixture).
When a test runs in a *function* loop, the middleware's ``BaseHTTPMiddleware``
awaits those session-loop-bound Futures → ``RuntimeError: got Future attached
to a different loop`` (6 direct failures).

Fix mirrors the ``customer_client`` / ``export_client`` twins (Gate-4
pass-3 canon): per-test NullPool engine + ``get_db`` override so every DB
connection is born in and dies in the test's own function-scoped loop.
``audit_mw.AsyncSessionLocal`` (which bypasses FastAPI DI) is patched to the
same NullPool session-maker so audit writes also stay in the function loop.

D1 fix (Gate-4 repair-1): NO SAVEPOINT on ``iam_client``.
The split-engine integration tests (``test_customer_cross_module_eligibility``,
``test_customer_full_onboarding_flow``) create a user via ``iam_client`` and then
read that user back via a SEPARATE engine on ``os.environ["DATABASE_URL"]``.
A SAVEPOINT outer-transaction would keep the user row uncommitted, making it
invisible to the second engine → ``ForeignKeyViolationError``.  The function-loop
NullPool engine alone is sufficient to kill the cross-loop error.  Real row
commits are acceptable because ``_cleanup_users_by_phone_prefix`` removes all
test data at teardown by phone prefix.

D2 fix (Gate-4 repair-1): patch ``_valkey_module._otp_client`` at the module
level.  ``rate_limit_mw._check_window`` calls ``await get_valkey_otp()`` as a
plain function call — NOT through FastAPI DI.  So the FastAPI
``dependency_overrides[get_valkey_otp]`` override has no effect on it.  When
test N's function loop closes, the ``_otp_client`` singleton retains a
``StreamWriter`` whose transport's ``_loop`` is the now-closed loop N.  When
test N+1 boots a new lifespan and the middleware makes a Valkey pipeline call,
that writer tries ``self._loop.call_soon(...)`` → ``RuntimeError: Event loop is
closed`` (13 teardown errors).  Patching ``_otp_client`` to a fresh
function-loop-bound client (exactly as we already patch ``_cache_client``)
prevents this — the singleton is always the current-loop client for the duration
of the test.
"""

from __future__ import annotations

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.core.middleware.audit_mw as _audit_mw
import app.shared.valkey as _valkey_module

# Import the app at module load; surface ImportError early.
from app.main import app
from app.shared.database import Base, get_db
from app.shared.models.audit_event import AuditEvent
from app.shared.models.user import User
from app.shared.valkey import get_valkey_otp
from tests.conftest import _DEV_DATABASE_URL, _valkey_base


_INTEGRATION_PHONE_PREFIX = "+9155500"
"""Every integration test uses this prefix — safe to DELETE-by-prefix."""


async def _cleanup_users_by_phone_prefix(
    db_url: str, prefix: str = _INTEGRATION_PHONE_PREFIX
) -> None:
    """DELETE audit_events + users whose phone starts with the test prefix.

    Order matters: ``audit_events.user_id`` is ``ON DELETE RESTRICT`` per
    §11.2 DDL (audit rows must survive user deletion for compliance), so
    the cleanup MUST delete the audit rows first.  This is acceptable for
    test data only — production code NEVER deletes users (DPDP delete is
    a §V1.5 right-to-erasure surface that anonymises rather than purges).

    Runs against the same DB the routes wrote to.
    Uses NullPool to avoid asyncpg loop-attachment issues — the cleanup runs
    in the test's function loop, not a session-scoped one.
    """
    engine = create_async_engine(db_url, poolclass=NullPool, echo=False)
    try:
        async with engine.connect() as conn:
            # Two-step delete: SELECT user IDs first, then DELETE dependents.
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

    * Boots the FastAPI lifespan once per fixture call.
    * Overrides ``Depends(get_db)`` with a function-loop NullPool engine +
      session-maker so every DB operation in this test is born in and dies in
      the function-scoped event loop.  This kills the ``got Future attached to
      a different loop`` cross-loop error that fires when routes resolve
      ``get_db`` against the app-global ``AsyncSessionLocal``
      (session-loop-bound engine).
    * NO SAVEPOINT isolation (D1 fix): rows are committed for real so that
      split-engine tests (``test_customer_cross_module_eligibility``) can read
      them back via an independent ``os.environ["DATABASE_URL"]`` connection.
      ``_cleanup_users_by_phone_prefix`` removes all test rows at teardown.
    * Patches ``audit_mw.AsyncSessionLocal`` to the same NullPool session-maker
      so middleware audit writes also stay in the function loop.
    * Patches ``_valkey_module._otp_client`` (D2 fix): ``rate_limit_mw`` calls
      ``get_valkey_otp()`` as a plain function — NOT through FastAPI DI — so
      the DI override alone does not protect it.  We replace the module-level
      singleton with a fresh function-loop-bound client, preventing
      ``RuntimeError: Event loop is closed`` on the next test's fixture setup.
    * Explicitly disposes ``app.state.db_engine`` + closes ``app.state.valkey``
      after the lifespan exits to drain pending asyncpg pool callbacks before
      the function loop tears down.
    * Cleans up users by phone prefix in teardown.
    """
    import redis.asyncio as _redis_lib

    db_url = _DEV_DATABASE_URL
    valkey_base = _valkey_base()

    # ── 1. Build function-loop NullPool engine ─────────────────────────────
    # NullPool: no connection reuse → no asyncpg Future loop-binding issues.
    # Provision-aware: when TEST_DATABASE_URL is set (CI), the alembic schema
    # already exists — skip drop_all/create_all to avoid wiping GIN indexes.
    engine = create_async_engine(db_url, poolclass=NullPool, echo=False)
    _provisioned = bool(os.environ.get("TEST_DATABASE_URL"))
    if not _provisioned:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    # ── 2. Plain commit-for-real session-maker (no SAVEPOINT) ─────────────
    # D1 fix: the split-engine eligibility + onboarding tests read inserted
    # rows back via a SEPARATE engine on os.environ["DATABASE_URL"].  Under
    # SAVEPOINT isolation those rows are never visible to the second engine
    # (uncommitted outer txn) → ForeignKeyViolationError.  The function-loop
    # NullPool engine alone is sufficient to fix the cross-loop error; the
    # SAVEPOINT layer is unnecessary and actively harmful here.
    TestSession = async_sessionmaker(engine, expire_on_commit=False)

    # ── 3. Override FastAPI DI ─────────────────────────────────────────────
    _otp_clients: list = []

    async def _otp_override():
        c = _redis_lib.from_url(f"{valkey_base}/0", decode_responses=True)
        _otp_clients.append(c)
        return c

    async def _db_override():
        session = TestSession()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    app.dependency_overrides[get_valkey_otp] = _otp_override
    app.dependency_overrides[get_db] = _db_override

    # ── 4. Patch module-level singletons that bypass DI ───────────────────
    # 4a. audit_mw uses AsyncSessionLocal directly (not via Depends).
    _original_audit_session_local = _audit_mw.AsyncSessionLocal
    _audit_mw.AsyncSessionLocal = TestSession  # type: ignore[attr-defined]

    # 4b. shared.valkey cache singleton (used by core/cache.py get_or_set).
    _original_cache_client = _valkey_module._cache_client
    _test_cache_client = _redis_lib.from_url(f"{valkey_base}/3", decode_responses=True)
    _valkey_module._cache_client = _test_cache_client  # type: ignore[assignment]

    # 4c. D2 fix: shared.valkey OTP singleton (used by rate_limit_mw directly,
    #     NOT through FastAPI DI).  Without this patch, after test N's function
    #     loop closes the old _otp_client's StreamWriter transport is bound to
    #     that closed loop; test N+1's rate_limit_mw pipeline call triggers
    #     `loop.call_soon()` on the closed loop → RuntimeError: Event loop is
    #     closed (13 teardown errors).  Replace with a fresh function-loop client.
    _original_otp_client = _valkey_module._otp_client
    _test_otp_client = _redis_lib.from_url(f"{valkey_base}/0", decode_responses=True)
    _valkey_module._otp_client = _test_otp_client  # type: ignore[assignment]

    # ── 5. Pre-test user cleanup ───────────────────────────────────────────
    # Run before boot to ensure prior run residue is removed.
    await _cleanup_users_by_phone_prefix(db_url)

    # ── 6. Boot lifespan + yield client ────────────────────────────────────
    lifespan_db_engine = None
    lifespan_valkey_client = None

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            async with app.router.lifespan_context(app):
                lifespan_db_engine = getattr(app.state, "db_engine", None)
                lifespan_valkey_client = getattr(app.state, "valkey", None)
                yield ac

            # ── Lifespan has exited (lifespan teardown ran dispose/aclose).
            # Explicitly dispose again INSIDE the function-loop async context
            # to drain any pending asyncpg pool callbacks before the loop
            # is torn down.
            if lifespan_db_engine is not None:
                try:
                    await lifespan_db_engine.dispose()
                except Exception:
                    pass
            if lifespan_valkey_client is not None:
                try:
                    await lifespan_valkey_client.aclose()
                except Exception:
                    pass

    finally:
        # ── 7. Teardown ───────────────────────────────────────────────────
        # Restore module-level singletons.
        _audit_mw.AsyncSessionLocal = _original_audit_session_local  # type: ignore[attr-defined]
        _valkey_module._cache_client = _original_cache_client  # type: ignore[assignment]
        _valkey_module._otp_client = _original_otp_client  # type: ignore[assignment]

        # Close OTP + cache + explicit OTP client created during the test.
        for c in _otp_clients:
            try:
                await c.aclose()
            except Exception:
                pass
        try:
            await _test_cache_client.aclose()
        except Exception:
            pass
        try:
            await _test_otp_client.aclose()
        except Exception:
            pass

        # Provision-aware schema teardown.
        if not _provisioned:
            try:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
            except Exception:
                pass
        try:
            await engine.dispose()
        except Exception:
            pass

        # Remove DI overrides.
        app.dependency_overrides.pop(get_valkey_otp, None)
        app.dependency_overrides.pop(get_db, None)

        # Post-test user cleanup.
        try:
            await _cleanup_users_by_phone_prefix(db_url)
        except Exception:
            pass
