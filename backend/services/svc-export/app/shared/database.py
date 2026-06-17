"""svc-export SQLAlchemy 2.0 async engine, session factory, FastAPI dependency.

Vendored from the monolith ``app.shared.database`` (BACKEND_ARCHITECTURE.md
§5.B).  Behaviour is identical; the only difference is the SMALL pool sizing
(svc-export is worker-heavy — see ``shared/config.py``).

Schema binding
--------------
The export repository queries the ``exports`` table which lives in the
``export`` Postgres schema after the Sub-Plan A schema-split migration.  The
schema is bound on the vendored ORM model (``app.shared.models.export``) via
``__table_args__ = {"schema": "export"}``, NOT on the engine — so the same
engine can also reach ``public.audit_events`` for the cross-schema audit
write in ``tasks.py``.

Celery worker variant — :func:`make_worker_session`
---------------------------------------------------
Uses ``NullPool`` because each Celery task runs inside its own
``asyncio.run()`` call (fresh event loop).  asyncpg's pool attaches internal
``Future`` objects to the loop that was current when the connection was
established; a recycled connection carrying a Future bound to a dead loop
raises ``RuntimeError: Task got Future attached to a different loop``.
``NullPool`` disables reuse entirely.  Locked verbatim from the monolith.
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
    """Declarative base for svc-export's vendored ORM models."""


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
    success, rolls back on exception, always closes.  Locked verbatim per §5.B.
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

    Creates a brand-new ``NullPool`` engine on every call so no asyncpg
    connection or ``Future`` is shared between separate ``asyncio.run()``
    invocations.  Disposed on exit.  Locked rationale: see module docstring.
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
