"""svc-pricing SQLAlchemy 2.0 async engine, session factory, FastAPI dependency.

Vendored from the monolith ``app.shared.database`` (BACKEND_ARCHITECTURE.md
§5.B).  Behaviour is identical; the only difference is the small pool sizing
(svc-pricing does a single-row read + single-row insert per request — see
``shared/config.py``).

Schema binding
--------------
pricing OWNS the ``pricing`` schema (the ``pricing_calcs`` table moved
``public`` → ``pricing`` in MS-D Phase A, migration ``97c9dd63f587``).  The
schema is bound on the vendored ORM model
(``PricingCalc.__table_args__ = {"schema": "pricing"}``), NOT on the engine.
The ``public`` tables the vendored core layer touches (``users`` for the auth
existence check, ``audit_events`` for the cross-schema audit INSERT) bind
``{"schema": "public"}`` on their own models.

NO ``make_worker_session``
--------------------------
The monolith ``shared/database`` exports a NullPool ``make_worker_session``
helper for the Celery worker path.  svc-pricing runs NO Celery worker (it is a
synchronous deterministic calculator — spec §0.2 / §0.8), so that helper is
intentionally NOT vendored here.
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
    """Declarative base for svc-pricing's vendored ORM models."""


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
