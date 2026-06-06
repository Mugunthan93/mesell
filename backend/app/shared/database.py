"""SQLAlchemy 2.0 async engine, session factory, and FastAPI dependency.

Per BACKEND_ARCHITECTURE.md §5.B, this module owns the **single** async
engine for the API tier and the **single** ``AsyncSessionLocal`` factory.
Every route handler + service that touches the database receives its session
via :func:`get_db`.  No other module instantiates an engine, a sessionmaker,
or a Session.

Engine sizing (§5.B locked)
---------------------------
* ``pool_size=10`` + ``max_overflow=5`` per replica.  Two API replicas → up
  to 30 concurrent DB connections from the API tier.
* ``pool_pre_ping=True`` — mandatory.  Detects stale connections after a
  Postgres pod restart without bouncing the process.
* ``pool_recycle=1800`` — 30 minutes.  Proactively cycles long-lived
  connections so we never hand out a dead one.
* ``expire_on_commit=False`` — mandatory.  SQLAlchemy 2.0's async
  relationship lifecycle cannot tolerate post-commit expiration without
  explicit ``session.refresh(...)`` calls, which the codebase does not
  pattern.

``get_db`` lifecycle (§5.B locked verbatim)
-------------------------------------------
The dependency yields a session, commits on success, rolls back on
exception, and closes in ``finally``.  This is the **commit-on-yield**
pattern — handlers do NOT call ``await db.commit()`` themselves; the
dependency owns the unit-of-work boundary.

Celery worker variant — :func:`make_worker_session`
---------------------------------------------------
The Celery-worker helper uses ``NullPool`` because each Celery task runs
inside its own ``asyncio.run()`` call, which creates and tears down a fresh
event loop.  asyncpg's pool attaches internal ``Future`` objects to the
loop that was current when the connection was established; a recycled
connection carrying a Future bound to a dead loop raises
``RuntimeError: Task got Future attached to a different loop``.  ``NullPool``
disables connection reuse entirely — every ``async with session:`` block
opens one new TCP connection and closes it on exit.  Per-task overhead
(~2 ms connect roundtrip) is negligible compared to the seconds-long
image/AI workloads inside the tasks.

Locked rule
-----------
NO other module creates an engine, a sessionmaker, or a Session.  NO other
module imports ``async_sessionmaker`` or ``create_async_engine`` from
``sqlalchemy.ext.asyncio``.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.shared.config import settings


# ── DeclarativeBase ────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Declarative base for all ORM models in :mod:`app.shared.models`.

    Re-exported by ``app.shared.models.base`` for the canonical model-side
    import path.  Alembic's ``env.py`` imports ``Base`` from this module to
    discover all table metadata for ``--autogenerate``.
    """


# ── FastAPI engine — persistent, pooled (do NOT use in Celery workers) ─────
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=settings.DB_ECHO,
)
"""Module-level async engine singleton.  Disposed at app shutdown."""

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
"""Module-level session factory.  Locked: ``expire_on_commit=False``."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an :class:`AsyncSession`, commits on
    success, rolls back on exception, always closes.

    Locked verbatim per §5.B.  Route handlers receive::

        db: AsyncSession = Depends(get_db)

    and do NOT call ``await db.commit()`` themselves.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Celery worker helper — NullPool engine ─────────────────────────────────
@asynccontextmanager
async def make_worker_session() -> AsyncIterator[AsyncSession]:
    """Async context manager — yields a session safe for Celery workers.

    Creates a brand-new engine with ``NullPool`` on every call so that no
    asyncpg connection or ``Future`` is shared between separate
    ``asyncio.run()`` invocations.  The engine is disposed on exit.

    Usage::

        async with make_worker_session() as db:
            obj = await db.get(MyModel, pk)
            ...
            # commits happen explicitly inside the task

    Locked rationale: see module docstring.
    """
    worker_engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
    )
    worker_session_maker = async_sessionmaker(
        worker_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    try:
        async with worker_session_maker() as session:
            yield session
    finally:
        await worker_engine.dispose()


__all__ = [
    "Base",
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "make_worker_session",
]
