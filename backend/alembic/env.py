"""Alembic environment configured for async SQLAlchemy."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.shared.config import settings
from app.shared.database import Base
from app.shared import models  # noqa: F401 — ensure all models are registered on Base.metadata

config = context.config

# NOTE: Do NOT call config.set_main_option("sqlalchemy.url", ...) here.
# The DATABASE_URL may contain percent-encoded characters (e.g. %2F in the
# password) that trigger configparser interpolation errors.  Instead we pass
# the URL directly to create_async_engine / context.configure below, bypassing
# configparser entirely.

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # transaction_per_migration=True: each revision gets its own
        # BEGIN/COMMIT, which is required for migrations that use
        # op.get_context().autocommit_block() (e.g. CREATE INDEX CONCURRENTLY).
        # Without this flag, all revisions share a single outer transaction and
        # autocommit_block() cannot commit the outer transaction independently.
        transaction_per_migration=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    # Build the engine directly from settings.DATABASE_URL so that
    # percent-encoded characters in the password are never fed through
    # configparser (which would mis-interpret them as interpolation markers).
    connectable = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
