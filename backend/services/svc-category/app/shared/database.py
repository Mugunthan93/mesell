"""svc-category SQLAlchemy 2.0 async engine, session factory, FastAPI dependency.

Vendored from the monolith ``app.shared.database`` (BACKEND_ARCHITECTURE.md
§5.B).  Behaviour is identical; the only difference is the read-heavy pool
sizing (svc-category is cache-fronted — see ``shared/config.py``).

Schema binding
--------------
The category repository queries the ``categories`` / ``templates`` /
``field_enum_values`` tables which live in the ``category`` Postgres schema
after the Sub-Plan F schema-split migration (``c4f1e7a9d302``).  The schema is
bound on each vendored ORM model via ``__table_args__ = {"schema":
"category"}``, NOT on the engine — so the same engine can also reach
``public.audit_events`` for the SHARED AI-budget cross-schema write in the
vendored ``ai_ops.cost_tracker`` (F3.c).

Worker helper — :func:`make_worker_session`
-------------------------------------------
svc-category runs NO Celery worker, but :func:`make_worker_session` is still
vendored: the startup cache pre-warm (``core.cache.prewarm_top_categories``,
§6.7) runs from the FastAPI lifespan context where ``get_db`` (request-scoped)
is unavailable, so it uses a peer ``NullPool`` worker session instead.
``NullPool`` avoids reusing an asyncpg connection whose internal ``Future`` is
bound to a dead event loop.  Locked verbatim from the monolith.
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
    """Declarative base for svc-category's vendored ORM models."""


# ── FastAPI engine — persistent, pooled ────────────────────────────────────
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


# ── Worker / lifespan helper — NullPool engine ─────────────────────────────
@asynccontextmanager
async def make_worker_session() -> AsyncIterator[AsyncSession]:
    """Async context manager — yields a session safe for lifespan/worker use.

    Creates a brand-new ``NullPool`` engine on every call so no asyncpg
    connection or ``Future`` is shared between separate ``asyncio.run()``
    invocations.  Disposed on exit.  Used by the startup cache pre-warm
    (§6.7).  Locked rationale: see module docstring.
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
