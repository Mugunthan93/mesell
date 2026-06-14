"""svc-iam SQLAlchemy 2.0 async engine, session factory, FastAPI dependency.

Vendored from the monolith ``app.shared.database`` (BACKEND_ARCHITECTURE.md
§5.B).  Behaviour is identical; the only difference is the small pool sizing
(svc-iam does a single-row read + single-row upsert per auth request — see
``shared/config.py``).

Schema binding
--------------
iam OWNS the ``iam`` schema (the ``users`` table moved ``public`` → ``iam`` in
MS-4 Phase A, migration ``b1c2d3e4f5a6``).  The schema is bound on the vendored
ORM model (``User.__table_args__ = {"schema": "iam"}``), NOT on the engine.
The ``public`` table the vendored core layer writes to (``audit_events`` for
the cross-schema §7.I audit INSERT) binds ``{"schema": "public"}`` on its own
model.

NO ``make_worker_session``
--------------------------
The monolith ``shared/database`` exports a NullPool ``make_worker_session``
helper for the Celery worker path.  svc-iam runs NO Celery worker (iam has no
``tasks.py`` — SUB_PLAN_0G §0.2), so that helper is intentionally NOT vendored
here.
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
    """Declarative base for svc-iam's vendored ORM models."""


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
