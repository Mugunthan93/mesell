"""Shared pytest fixtures: ephemeral DB, in-memory Valkey, FastAPI test client."""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Force dev mode + isolated test schema before importing app modules.
os.environ.setdefault("APP_ENV", "development")
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://meesell:password@localhost:5432/meesell",
)
os.environ.setdefault("VALKEY_URL", "redis://localhost:6381/15")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use")
# Redirect Celery tasks to isolated DBs so the GCP worker never picks up test jobs.
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6381/11")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6381/12")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app import models as _models  # noqa: F401,E402 — registers tables on Base.metadata

# app.main imports legacy routers that reference deleted model files (sku.py,
# image.py) from the pre-V1 era.  Those routers are out-of-scope for the
# database track.  Guard the import so that the database smoke tests
# (test_database.py) can load conftest without error.  The client/auth_client
# fixtures that depend on app will be skipped automatically when app is None.
try:
    from app.main import app  # noqa: E402
    _APP_IMPORT_ERROR: Exception | None = None
except Exception as _exc:  # noqa: BLE001
    app = None  # type: ignore[assignment]
    _APP_IMPORT_ERROR = _exc

# ── Dev Postgres URL ──────────────────────────────────────────────────────────
# Used by Phase 4 smoke tests.  Overridable via DEV_DATABASE_URL env var so
# that CI can point at a different host if needed.  On the founder's laptop the
# port-forward exposes the K3s dev Postgres as localhost:5433.
_DEV_DATABASE_URL = os.environ.get(
    "DEV_DATABASE_URL",
    "postgresql+asyncpg://meesell:j3w%2F6o%2F7k%2FJwjPu1J4OqDpFStho7IsK%2F0lRYnwmbN6Q%3D@localhost:5433/meesell",
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
    if app is None:
        pytest.skip(
            f"app.main could not be imported (legacy router import error): {_APP_IMPORT_ERROR}"
        )
    Session = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        # Drive lifespan manually so app.state.valkey is set up.
        async with app.router.lifespan_context(app):
            yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(client):
    phone = "+919876543210"
    await client.post("/api/v1/auth/otp/send", json={"phone": phone})
    resp = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "1234"})
    token = resp.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    client.test_user_id = resp.json()["user"]["id"]
    return client


# ── Phase 4 smoke-test fixtures ───────────────────────────────────────────────
# These fixtures hit the live dev Postgres (port-forwarded K3s instance).
# The `db` fixture wraps every test in a transaction that is ROLLED BACK on
# teardown — no test data ever persists to the shared dev DB.
#
# Architecture:
#   dev_engine (session scope)  — Used ONLY by seeded-data tests (section H)
#                                  for read-only queries.  Created in the
#                                  session event loop.
#   db         (function scope) — Creates its own NullPool engine, one
#                                  connection, one transaction.  Everything is
#                                  created and destroyed within the SAME
#                                  function-scoped event loop that pytest-asyncio
#                                  0.24 assigns to each test.  This avoids all
#                                  cross-loop Future attachment issues.
#
# Why per-test NullPool engine (not a session-scoped pool):
#   pytest-asyncio 0.24 with asyncio_default_fixture_loop_scope=session runs
#   SESSION-scoped fixtures in the session event loop, but FUNCTION-scoped
#   fixtures (and tests) each run in a freshly created function-scoped event
#   loop.  asyncpg Protocols (and their Futures) are attached to the loop that
#   is running when the connection is first established.  If a session-scoped
#   engine is used and its pool Protocols were created in the session loop, any
#   attempt to await them from a function-scoped loop raises:
#     RuntimeError: Task ... got Future ... attached to a different loop
#   The fix: create a fresh NullPool engine INSIDE the function-scoped `db`
#   fixture — the engine, connection, and all Futures are born in the same
#   function loop and disposed before that loop closes.
#
# Important: tests must use session.flush() not session.commit().  commit()
# would commit the transaction, defeating the rollback.


@pytest_asyncio.fixture(scope="session")
async def dev_engine():
    """Session-scoped engine for seeded-data tests (section H read-only queries).

    Uses NullPool to avoid asyncpg loop attachment issues: since section H
    tests are plain SELECT statements that don't write anything, there is no
    need for a transaction — each query opens/closes a connection atomically.
    """
    eng = create_async_engine(_DEV_DATABASE_URL, poolclass=NullPool, echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def db() -> AsyncSession:
    """Per-test async session with a fresh NullPool engine + ROLLBACK on teardown.

    Each test gets its own engine (NullPool), connection, and transaction.
    All engine/connection/Future objects are created and destroyed within the
    same function-scoped event loop.

    loop_scope="function" is set explicitly so that asyncpg Protocols, Futures,
    and Tasks are all attached to the same function-scoped event loop that
    pytest-asyncio 0.24 uses to run each test.  Without this, the session-scoped
    default loop (asyncio_default_fixture_loop_scope=session in pytest.ini) would
    create a loop-mismatch with the function-scoped loop used by the test runner.
    """
    eng = create_async_engine(_DEV_DATABASE_URL, poolclass=NullPool, echo=False)
    try:
        async with eng.connect() as conn:
            await conn.begin()
            Session = async_sessionmaker(
                bind=conn, expire_on_commit=False, class_=AsyncSession
            )
            session = Session()
            try:
                yield session
            finally:
                await session.close()
                await conn.rollback()
    finally:
        await eng.dispose()
