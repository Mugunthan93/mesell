"""SQLAlchemy async engine, session factory, and FastAPI dependency.

Two engine configurations are provided:

* ``engine`` / ``async_session_maker`` — used by the FastAPI application.
  A standard QueuedPool (pool_size=10) that lives for the lifetime of the
  ASGI process.  Never use these in Celery workers (see note below).

* :func:`make_worker_session` — used by Celery tasks.
  Each call creates a *throw-away* engine backed by ``NullPool`` so that
  asyncpg never holds a connection object across ``asyncio.run()`` calls.
  ``asyncio.run()`` creates and closes a fresh event loop on every
  invocation.  asyncpg's ``QueuedPool`` attaches internal ``Future``
  objects to the loop that was current when the connection was established;
  if that loop is later closed (as ``asyncio.run()`` always does) and the
  engine is re-used by a subsequent ``asyncio.run()`` call, the recycled
  connection carries a ``Future`` bound to the dead loop →
  ``RuntimeError: Task got Future attached to a different loop``.

  ``NullPool`` disables connection reuse entirely: every ``async with
  session:`` block opens one new TCP connection and closes it on exit.
  The per-task overhead (~2 ms connect roundtrip) is negligible compared
  to the seconds-long image/AI workloads.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


# ---------------------------------------------------------------------------
# FastAPI engine — persistent, pooled (do NOT use in Celery workers)
# ---------------------------------------------------------------------------

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=5,
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Celery worker helper — NullPool engine (safe across asyncio.run() calls)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def make_worker_session() -> AsyncIterator[AsyncSession]:
    """Async context manager that yields a DB session safe for Celery workers.

    Creates a brand-new engine with ``NullPool`` on every call so that no
    asyncpg connection or ``Future`` is shared between separate
    ``asyncio.run()`` invocations.  The engine is disposed on exit.

    Usage::

        async with make_worker_session() as db:
            obj = await db.get(MyModel, pk)
            ...
            await db.commit()
    """
    worker_engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
    )
    worker_session_maker = async_sessionmaker(
        worker_engine, class_=AsyncSession, expire_on_commit=False
    )
    try:
        async with worker_session_maker() as session:
            yield session
    finally:
        await worker_engine.dispose()
