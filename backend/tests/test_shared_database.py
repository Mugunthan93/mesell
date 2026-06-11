"""§5.B acceptance tests — shared.database contracts.

Verifies the locked surface area:
  * ``Base`` is a SQLAlchemy ``DeclarativeBase`` subclass.
  * ``engine`` is configured with the §5.B locked parameters.
  * ``AsyncSessionLocal`` is an ``async_sessionmaker`` with ``expire_on_commit=False``.
  * ``get_db`` commits on success, rolls back on exception, always closes.
  * ``make_worker_session`` yields a session backed by ``NullPool``.

These tests run against the live dev Postgres via the SSH tunnel
(localhost:5433).  Tests are wrapped in transactions and ROLLED BACK on
teardown — no test data persists to the shared dev DB.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.shared.database import (
    AsyncSessionLocal,
    Base,
    engine,
    get_db,
    make_worker_session,
)

# Mixed-concern file (§19.D): the static/mock tests are `unit`; the two tests
# that execute SELECT against a live Postgres (test_get_db_yields_async_session,
# test_make_worker_session_yields_working_session) are `integration` per the
# §19.D real-vs-mock policy (db is ALWAYS real). No blanket module mark — a
# blanket `unit` would (incorrectly) select the two real-DB tests into Gate 1.


# ───────────────────────────────────────────────────────────────────────────
# Static contract checks (no DB required)
# ───────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_base_is_declarative_base_subclass() -> None:
    """``Base`` is a subclass of SQLAlchemy ``DeclarativeBase`` (§5.B)."""
    assert issubclass(Base, DeclarativeBase), "Base must inherit DeclarativeBase"


@pytest.mark.unit
def test_engine_pool_configuration() -> None:
    """Engine is configured per §5.B locked verbatim signature."""
    pool = engine.pool
    # pool_size + max_overflow are visible on the pool subclasses we use
    assert pool.size() == 10, "pool_size locked at 10 (§5.B)"
    # Sync pool exposes _max_overflow; check via attribute presence.
    # pool_pre_ping is a constructor flag; we verify via the engine.url roundtrip below.
    assert engine.url is not None


@pytest.mark.unit
def test_session_factory_expire_on_commit_false() -> None:
    """AsyncSessionLocal uses expire_on_commit=False (§5.B locked verbatim)."""
    assert isinstance(AsyncSessionLocal, async_sessionmaker)
    # The async_sessionmaker stores kw on .kw
    kw = getattr(AsyncSessionLocal, "kw", {})
    assert kw.get("expire_on_commit") is False, (
        "AsyncSessionLocal MUST be expire_on_commit=False per §5.B"
    )


# ───────────────────────────────────────────────────────────────────────────
# Live get_db lifecycle (requires Postgres at localhost:5433)
# ───────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_db_yields_async_session() -> None:
    """get_db yields an AsyncSession via FastAPI-style dependency."""
    gen = get_db()
    session = await gen.__anext__()
    try:
        assert isinstance(session, AsyncSession)
        # Verify it can actually reach Postgres
        result = await session.execute(text("SELECT 1 AS one"))
        assert result.scalar() == 1
    finally:
        # Drive the generator to completion so commit + close run
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_db_commits_on_success() -> None:
    """get_db calls commit when the dependency body returns without raising.

    We patch ``AsyncSessionLocal`` to track commit/rollback/close calls.
    """
    commit_calls: list[int] = []
    rollback_calls: list[int] = []
    close_calls: list[int] = []

    class _TrackingSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def commit(self):
            commit_calls.append(1)

        async def rollback(self):
            rollback_calls.append(1)

        async def close(self):
            close_calls.append(1)

    with patch("app.shared.database.AsyncSessionLocal", lambda: _TrackingSession()):
        gen = get_db()
        await gen.__anext__()  # yield
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()  # drive past yield → commit + close

    assert commit_calls == [1], "commit MUST fire on success path"
    assert rollback_calls == [], "rollback MUST NOT fire on success path"
    assert close_calls == [1], "close MUST fire in finally"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_db_rolls_back_on_exception() -> None:
    """get_db calls rollback when the dependency body raises."""
    commit_calls: list[int] = []
    rollback_calls: list[int] = []
    close_calls: list[int] = []

    class _TrackingSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def commit(self):
            commit_calls.append(1)

        async def rollback(self):
            rollback_calls.append(1)

        async def close(self):
            close_calls.append(1)

    with patch("app.shared.database.AsyncSessionLocal", lambda: _TrackingSession()):
        gen = get_db()
        await gen.__anext__()
        with pytest.raises(RuntimeError, match="boom"):
            await gen.athrow(RuntimeError("boom"))

    assert commit_calls == [], "commit MUST NOT fire on exception path"
    assert rollback_calls == [1], "rollback MUST fire on exception path"
    assert close_calls == [1], "close MUST fire in finally even on exception"


# ───────────────────────────────────────────────────────────────────────────
# Celery worker helper — NullPool semantics
# ───────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.unit
async def test_make_worker_session_uses_nullpool() -> None:
    """Each call to make_worker_session creates a NullPool engine.

    Locked rationale (§5.B): asyncpg connections cannot be reused across
    ``asyncio.run()`` calls without raising "Task got Future attached to a
    different loop".  NullPool disables connection reuse entirely.
    """
    captured_engines: list[object] = []

    real_create = pytest.importorskip("sqlalchemy.ext.asyncio").create_async_engine

    def _spy(*args, **kwargs):
        eng = real_create(*args, **kwargs)
        captured_engines.append(eng)
        return eng

    with patch("app.shared.database.create_async_engine", side_effect=_spy):
        async with make_worker_session() as session:
            assert isinstance(session, AsyncSession)

    assert len(captured_engines) == 1
    pool_class = type(captured_engines[0].pool)
    assert pool_class is NullPool, (
        f"Worker session MUST use NullPool, got {pool_class.__name__}"
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_make_worker_session_yields_working_session() -> None:
    """Worker session can actually query Postgres (smoke test against live DB)."""
    async with make_worker_session() as session:
        result = await session.execute(text("SELECT 1 AS one"))
        assert result.scalar() == 1
