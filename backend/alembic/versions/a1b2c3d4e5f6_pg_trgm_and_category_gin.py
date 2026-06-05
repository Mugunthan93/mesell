"""pg_trgm_and_category_gin

Adds the pg_trgm extension and three GIN trigram indexes on the categories
table for the Manual Browse search endpoint (§7.4 of docs/MVP_ARCHITECTURE.md).

Revision ID: a1b2c3d4e5f6
Revises: 935e55b4852c
Create Date: 2026-06-05 07:45:00.000000

--- TRANSACTIONAL DDL PATTERN CHOSEN ---

CREATE INDEX CONCURRENTLY cannot run inside an open transaction block.

Pattern used: op.get_context().autocommit_block() (Alembic 1.13 documented API).

This is the officially recommended Alembic pattern for any DDL that must run
outside a transaction (PostgreSQL CONCURRENTLY operations, ADD VALUE for enum
types, etc.).  It commits the preceding transaction, switches the connection to
AUTOCOMMIT, yields, then restores the prior transaction state.

Requirement: env.py must set transaction_per_migration=True in
context.configure().  Without this, autocommit_block() commits the single
outer transaction that wraps ALL pending revisions, not just this revision's
sub-transaction.  With transaction_per_migration=True, each revision has its
own BEGIN/COMMIT, so autocommit_block() commits only this revision's work.

env.py was updated to add transaction_per_migration=True in do_run_migrations().
This is safe for all existing migrations — it just means each revision is
committed independently rather than all revisions in a single outer transaction.

References:
  - https://alembic.sqlalchemy.org/en/latest/api/runtime.html#alembic.runtime.migration.MigrationContext.autocommit_block
  - §7.4 of docs/MVP_ARCHITECTURE.md (index DDL specification)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "935e55b4852c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Enable pg_trgm extension (runs inside the current transaction —
    # extension creates are transactional in PostgreSQL 16 and are committed
    # implicitly when autocommit_block() commits below).
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Step 2: Create the three GIN trigram indexes CONCURRENTLY.
    # autocommit_block() commits the preceding transaction (which includes the
    # CREATE EXTENSION above), switches to AUTOCOMMIT, then restores the
    # transaction state after the block exits.
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_path_trgm"
            " ON categories USING GIN (path gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_leaf_name_trgm"
            " ON categories USING GIN (leaf_name gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_super_name_trgm"
            " ON categories USING GIN (super_name gin_trgm_ops)"
        )


def downgrade() -> None:
    # Drop the three GIN trigram indexes CONCURRENTLY (non-blocking).
    with op.get_context().autocommit_block():
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS idx_categories_super_name_trgm"
        )
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS idx_categories_leaf_name_trgm"
        )
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS idx_categories_path_trgm"
        )
        # Drop the pg_trgm extension without CASCADE (RESTRICT is the default).
        # PostgreSQL will refuse the drop if any other object depends on the
        # extension, which is the safe behaviour — we never want to cascade-drop
        # indexes from other migrations.
        op.execute("DROP EXTENSION IF EXISTS pg_trgm RESTRICT")
