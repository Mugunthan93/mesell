"""Alembic environment for the svc-iam standalone migration chain.

Key differences from the monolith alembic/env.py:
  1. version_table_schema="iam" — the alembic_version tracking table
     lands inside the ``iam`` Postgres schema, not ``public``.  This
     prevents the svc-iam chain from colliding with the monolith chain's
     alembic_version row.
  2. No SQLAlchemy ORM metadata is wired (target_metadata=None).  svc-iam
     migrations are hand-authored DDL; there is no ORM Base here to
     autogenerate from.
  3. DATABASE_URL is injected via the environment variable of the same name.
     It MUST point at a Postgres connection where the iam_user role has
     rights on the public and iam schemas.

NOTE: Do NOT call config.set_main_option("sqlalchemy.url", ...) here.
The DATABASE_URL may contain percent-encoded characters (e.g. %2F in the
password) that trigger configparser interpolation errors.  Instead the URL
is passed directly to create_async_engine, bypassing configparser entirely.
(Mirrors the fix applied to the monolith env.py in Phase 2 — see
database-builder MEMORY §Phase 2 for the root-cause analysis.)

CRITICAL GOTCHA (SP01 lesson, MEMORY §MS Sub-Plan A Phase A):
  CREATE SCHEMA IF NOT EXISTS iam + connection.commit() MUST run BEFORE
  context.configure().  Alembic's internal _ensure_version_table() runs
  at configure-time and needs iam.alembic_version creatable — if the
  schema does not exist yet, Postgres errors before any migration code
  runs.  The commit() makes the schema DDL visible to configure-time
  internal queries (asyncpg implicit-transaction visibility).
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

import sqlalchemy as sa
from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No ORM metadata for svc-iam migrations — all DDL is explicit.
target_metadata = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_IAM_SCHEMA = "iam"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_database_url() -> str:
    """Return DATABASE_URL from the environment.

    Raises RuntimeError if the variable is not set, so the error is
    immediately visible rather than producing a cryptic Alembic message.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is required to run svc-iam "
            "Alembic migrations.  Set it to the async PostgreSQL connection "
            "string (postgresql+asyncpg://...) before invoking alembic."
        )
    return url


# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in offline / --sql mode.

    Emits SQL to stdout without connecting to a live database.
    Useful for generating SQL to review before applying.
    """
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # version_table_schema: alembic_version row lives in the iam
        # schema so it does not collide with the monolith's public.alembic_version.
        version_table_schema=_IAM_SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # Pre-create the iam schema before Alembic attempts to create the
    # version tracking table (iam.alembic_version).  Alembic's internal
    # _ensure_version_table runs BEFORE upgrade(), so the schema must exist
    # at configure-time, not just inside the migration function.
    #
    # CRITICAL (SP01 lesson): the commit() here is REQUIRED so the schema
    # creation DDL is visible to configure-time internal queries under
    # asyncpg's implicit-transaction semantics.
    connection.execute(sa.text("CREATE SCHEMA IF NOT EXISTS iam"))
    connection.commit()

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # version_table_schema: alembic_version row lands in iam schema,
        # not public — so it never collides with the monolith chain.
        version_table_schema=_IAM_SCHEMA,
        # transaction_per_migration: each revision gets its own BEGIN/COMMIT.
        # Required for future CONCURRENTLY index migrations (MEMORY Session 2).
        transaction_per_migration=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    url = _get_database_url()
    connectable = create_async_engine(
        url,
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
