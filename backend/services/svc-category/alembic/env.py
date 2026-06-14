"""Alembic environment for the svc-category standalone migration chain.

Key differences from the monolith alembic/env.py:
  1. version_table_schema="category" — the alembic_version tracking table
     lands inside the ``category`` Postgres schema, not ``public``.  This
     prevents the svc-category chain from colliding with the monolith chain's
     alembic_version row OR any other svc's alembic_version.
  2. No SQLAlchemy ORM metadata is wired (target_metadata = None).
     svc-category migrations are hand-authored DDL; there is no local ORM
     Base here to autogenerate from.
  3. DATABASE_URL is injected via the environment variable of the same name.
     It MUST point at a Postgres role that has ALTER TABLE rights on the 4
     tables being moved (or a superuser role for dev convenience).

NOTE: Do NOT call config.set_main_option("sqlalchemy.url", ...) here.
The DATABASE_URL may contain percent-encoded characters (e.g. %2F in the
password) that trigger configparser interpolation errors.  Instead the URL
is passed directly to create_async_engine, bypassing configparser entirely.
(Mirrors the fix applied to the monolith env.py in Phase 2 — see
database-builder MEMORY §Phase 2 for the root-cause analysis.)

CRITICAL LOAD-BEARING GOTCHA (from MS-A pilot, database-builder MEMORY):
The CREATE SCHEMA DDL + connection.commit() MUST occur BEFORE context.configure().
Alembic's _ensure_version_table() runs at configure-time and tries to create
category.alembic_version — if the category schema does not exist yet, Postgres
raises an error before any migration code executes.  Fix: issue CREATE SCHEMA IF
NOT EXISTS + commit() in do_run_migrations() BEFORE calling context.configure().
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

# No ORM metadata for svc-category migrations — all DDL is explicit.
target_metadata = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CATEGORY_SCHEMA = "category"


def _get_database_url() -> str:
    """Return DATABASE_URL from the environment.

    Raises RuntimeError if the variable is not set, so the error is
    immediately visible rather than producing a cryptic Alembic message.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is required to run svc-category "
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
        # version_table_schema: alembic_version row lives in the category
        # schema so it does not collide with the monolith's public.alembic_version
        # or any other svc chain's alembic_version.
        version_table_schema=_CATEGORY_SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run Alembic migrations synchronously against an open connection.

    LOAD-BEARING ORDER:
    1. CREATE SCHEMA IF NOT EXISTS category + commit()  — MUST come before
       context.configure() so that _ensure_version_table() can write
       category.alembic_version.  (MS-A pilot gotcha; database-builder MEMORY.)
    2. context.configure(version_table_schema="category", ...)
    3. context.begin_transaction() + run_migrations()
    """
    # Step 1 — Pre-create the category schema BEFORE context.configure().
    # The commit is required so the DDL is visible to Alembic's internal
    # configure-time queries (asyncpg implicit-transaction visibility rule).
    connection.execute(sa.text(f"CREATE SCHEMA IF NOT EXISTS {_CATEGORY_SCHEMA}"))
    connection.commit()

    # Step 2 — Configure Alembic context.
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # version_table_schema: the alembic_version row tracks this chain
        # inside category.alembic_version, isolated from all other chains.
        version_table_schema=_CATEGORY_SCHEMA,  # <-- THE KEY SETTING (spec §3.C)
        # transaction_per_migration: each revision gets its own BEGIN/COMMIT.
        # Required so that any future CONCURRENTLY index migrations work
        # (mirrors the monolith env.py setting from Session 2 G4 pass).
        transaction_per_migration=True,
    )

    # Step 3 — Run migrations.
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Async entry point: create engine, connect, run migrations."""
    url = _get_database_url()
    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Synchronous entry point called by Alembic CLI."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
