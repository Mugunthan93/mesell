"""Shared pytest fixtures: ephemeral DB, in-memory Valkey, FastAPI test client."""

from __future__ import annotations

import asyncio
import os

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

from app.shared.database import Base, get_db  # noqa: E402
from app.shared import models as _models  # noqa: F401,E402 — registers tables on Base.metadata

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
async def auth_client(client, use_live_valkey):
    """Authenticated test client per §7 iam FE-D5 contract.

    Bypasses /otp/send (avoids MSG91 vendor call) by pre-seeding the OTP
    record into Valkey DB 0 directly, then calls /otp/verify and pins the
    returned ``access_token`` as Bearer on every subsequent request.
    """
    import hashlib
    import json as _json
    import time as _time

    from app.shared import valkey as _vk_mod

    phone = "+919876543210"
    otp = "999000"
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    payload = _json.dumps(
        {"otp_hash": otp_hash, "attempts": 0, "expires_at": int(_time.time()) + 300}
    )
    valkey = await _vk_mod.get_valkey_otp()
    await valkey.set(f"otp:{phone}", payload, ex=300)

    resp = await client.post(
        "/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp}
    )
    body = resp.json()
    client.headers["Authorization"] = f"Bearer {body['access_token']}"
    # Resolve user_id via /me so tests can assert ownership without leaking JWT.
    me_resp = await client.get("/api/v1/auth/me")
    client.test_user_id = me_resp.json()["user_id"]  # type: ignore[attr-defined]
    return client


# ── §4 core/ fixtures ─────────────────────────────────────────────────────────
# ``use_live_valkey`` replaces the ``shared.valkey`` factory functions with
# per-test factories that create a FRESH Redis client IN THE CURRENT EVENT
# LOOP on every call.  The substitution is performed via ``monkeypatch`` —
# automatically reverted by pytest on teardown.  No module-level singleton
# survives the test, so a session-loop-bound client from an earlier test
# (e.g. ``test_database.py`` activating ``dev_engine`` in the session loop)
# can NEVER leak into a function-scoped test body.
#
# Why per-call fresh client (not pivot-the-singleton):
#   asyncpg / redis-py Protocols attach to whatever loop is running when the
#   first await on the connection happens.  If a singleton is built in the
#   session loop, awaiting it later from a function loop raises
#       RuntimeError: Task ... got Future ... attached to a different loop
#   By building each client inside the current (function-scoped) loop the
#   Future <-> loop attachment is always correct.
#
# Why monkeypatch the consumer modules too:
#   Every consumer in ``app/core/`` and the test modules themselves did
#   ``from app.shared.valkey import get_valkey_otp`` at import time, which
#   binds a LOCAL name in their own namespace.  Patching only
#   ``app.shared.valkey.get_valkey_otp`` would miss those captured refs.
#   We patch the name in every consumer namespace.

@pytest_asyncio.fixture(loop_scope="function")
async def use_live_valkey(monkeypatch):
    """Per-test live Redis at CORE_TEST_VALKEY_URL (default redis://localhost:6379).

    Monkeypatches ``get_valkey_otp`` / ``get_valkey_cache`` in ``app.shared.valkey``
    AND in every consumer module that captured the function by name at import
    time, to return a Redis client created IN THE CURRENT EVENT LOOP per call.
    No module singleton mutation survives — the patch is reverted by pytest's
    monkeypatch on teardown, guaranteeing zero cross-test loop pollution.
    Clients are ``aclose``d in teardown before the loop dies.
    """
    import redis.asyncio as _redis_lib  # local import — keeps top of conftest light
    import app.shared.valkey as _valkey_mod

    base = os.environ.get("CORE_TEST_VALKEY_URL", "redis://localhost:6379")
    created: list = []

    async def _otp():
        c = _redis_lib.from_url(f"{base}/0", decode_responses=True)
        created.append(c)
        return c

    async def _cache():
        c = _redis_lib.from_url(f"{base}/3", decode_responses=True)
        created.append(c)
        return c

    # 1. Patch the source module.
    monkeypatch.setattr(_valkey_mod, "get_valkey_otp", _otp)
    monkeypatch.setattr(_valkey_mod, "get_valkey_cache", _cache)

    # 2. Patch every consumer module that captured the function by name at
    #    import time (``from app.shared.valkey import get_valkey_*``).
    #    We import each consumer lazily so conftest module-load stays cheap
    #    and so a missing consumer (e.g. test runs without the middleware
    #    being importable) does not block the fixture.
    for mod_path, fn_name, factory in (
        ("app.core.cache", "get_valkey_cache", _cache),
        ("app.core.plan_guard", "get_valkey_otp", _otp),
        ("app.core.middleware.rate_limit_mw", "get_valkey_otp", _otp),
        ("app.core.middleware.audit_mw", "get_valkey_otp", _otp),
        # §7 iam router — captured ``get_valkey_otp`` at import time.
        ("app.modules.iam.router", "get_valkey_otp", _otp),
    ):
        try:
            mod = __import__(mod_path, fromlist=[fn_name])
        except Exception:
            continue
        if hasattr(mod, fn_name):
            monkeypatch.setattr(mod, fn_name, factory)

    # 3. Patch test modules that bound the same names at import time so
    #    helper calls inside the tests also see the fresh-per-call factory.
    #    pytest loads test files as TOP-LEVEL modules (bare ``test_core_cache``,
    #    not ``tests.test_core_cache``) when ``testpaths = tests`` is set
    #    without ``__init__.py`` packages — so look both up in sys.modules.
    import sys as _sys
    for mod_name, fn_name, factory in (
        ("test_core_cache", "get_valkey_cache", _cache),
        ("test_core_plan_guard", "get_valkey_otp", _otp),
    ):
        # Try both flat and dotted variants.
        for candidate in (mod_name, f"tests.{mod_name}"):
            mod = _sys.modules.get(candidate)
            if mod is not None and hasattr(mod, fn_name):
                monkeypatch.setattr(mod, fn_name, factory)

    # 4. Defensively NUKE any singleton that a previous test/session-scope
    #    fixture bound to a (potentially dead) loop.  We do NOT restore them
    #    — any future code path that bypasses the patched factory will
    #    re-create lazily, which still happens in a live loop.
    _valkey_mod._otp_client = None
    _valkey_mod._cache_client = None

    # 5. Pre-flush scratch DBs so each test sees a clean slate.
    pre_otp = await _otp()
    pre_cache = await _cache()
    try:
        await pre_otp.flushdb()
        await pre_cache.flushdb()
    except Exception:
        pass

    yield

    # 6. Teardown — flush + aclose every client created during the test.
    #    Run before the function loop dies; swallow errors to keep teardown
    #    robust if Valkey vanished mid-test.
    for c in created:
        try:
            await c.flushdb()
        except Exception:
            pass
        try:
            await c.aclose()
        except Exception:
            pass


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
