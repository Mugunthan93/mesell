"""svc-dashboard SQLAlchemy 2.0 async engine, session factory, FastAPI dependency.

Vendored from the monolith ``app.shared.database`` (BACKEND_ARCHITECTURE.md
§5.B).  Behaviour is identical; the only difference is the TINY pool sizing
(svc-dashboard does NO owned data access — see ``shared/config.py``).

Schema binding
--------------
dashboard owns ZERO tables (§13.D).  The engine backs only the vendored
``core/auth.get_current_user`` existence check (``db.get(User, sub)`` against
``public.users``) and the ``audit_mw`` cross-schema write to
``public.audit_events``.  Neither is a dashboard-owned schema; the schema is
bound on the vendored ORM models (``__table_args__ = {"schema": "public"}``),
NOT on the engine.

NO ``make_worker_session``
--------------------------
The monolith ``shared/database`` exports a NullPool ``make_worker_session``
helper for the Celery worker path.  svc-dashboard runs NO Celery worker (it is
a pure read — §13.I), so that helper is intentionally NOT vendored here.
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
    """Declarative base for svc-dashboard's vendored ORM models."""


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
