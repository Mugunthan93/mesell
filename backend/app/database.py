"""SQLAlchemy async engine, session factory, and FastAPI dependency."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


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


@asynccontextmanager
async def worker_session():
    """Async context manager for Celery worker tasks.

    Celery uses prefork — the module-level ``engine`` is inherited across the
    ``fork()`` boundary.  Asyncpg connections carry event-loop references; any
    connection (or even a pooled slot) touched before the fork will raise
    "Future attached to a different loop" inside the child's ``asyncio.run()``.

    Fix: use ``NullPool`` so SQLAlchemy never holds a connection between calls.
    Every ``connect()`` opens a brand-new asyncpg connection on the *current*
    event loop, and every ``close()`` disposes it immediately — no inherited
    state whatsoever.
    """
    from sqlalchemy.pool import NullPool

    _eng = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
    )
    _maker = async_sessionmaker(_eng, class_=AsyncSession, expire_on_commit=False)
    try:
        async with _maker() as session:
            yield session
    finally:
        await _eng.dispose()
