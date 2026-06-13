"""svc-customer SQLAlchemy 2.0 async engine, session factory, FastAPI dependency.

Vendored from the monolith ``app.shared.database`` (BACKEND_ARCHITECTURE.md
§5.B).  Behaviour is identical.

Schema binding
--------------
customer OWNS the ``customer`` schema.  ``customer.seller_profile`` was moved
from ``public`` by migration ``a9f3b2c5e1d8``; the schema is bound on the
vendored ORM model (``__table_args__`` ``{"schema": "customer"}``), NOT on the
engine.  The vendored ``public`` models (``User``, ``AuditEvent``) bind to
``public`` on their own ``__table_args__``.

NO ``make_worker_session``
--------------------------
The monolith ``shared/database`` exports a NullPool ``make_worker_session``
helper for the Celery worker path.  svc-customer runs NO Celery worker (it has
no background jobs), so that helper is intentionally NOT vendored here.
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.shared.config import settings


# ── DeclarativeBase ────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Declarative base for svc-customer's vendored ORM models."""


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


__all__ = [
    "Base",
    "engine",
    "AsyncSessionLocal",
    "get_db",
]
