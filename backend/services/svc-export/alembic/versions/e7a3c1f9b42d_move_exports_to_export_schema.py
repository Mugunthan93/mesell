"""Move exports table from public schema to export schema.

This is the first (and currently only) migration in the svc-export standalone
Alembic chain.  It is SEPARATE from the monolith chain (head f31c75438e61).

Context
-------
MASTER_PLAN §2.D assigns the ``exports`` table to Postgres schema ``export``
as part of the V1.5 schema-per-service isolation strategy.  This migration
effects that move.  The monolith's ``public.exports`` is moved; the monolith's
Alembic chain is NOT touched.

The migration is authored per spec §3.C (database-builder dispatch) from
backend-coordinator spec_msA_backend.md.

Risk #5 integrity pre-scan (§6 of SUB_PLAN_01)
-----------------------------------------------
Before the schema move we verify that every ``exports.user_id`` resolves to a
real row in ``public.users``.  The ``exports`` table was authored without a
cross-schema-durable FK (the FK will be dropped as part of schema isolation
per MASTER_PLAN §2.D), so we check referential integrity at the application
layer in this migration.

If orphaned rows are found the migration logs them and raises, aborting the
transaction cleanly.  Do NOT proceed with the schema move if orphans exist —
they indicate a data integrity problem that must be resolved manually before
extraction.

Upgrade
-------
1. Risk#5 scan: SELECT count of exports rows whose user_id has no match in
   users.  Raise if orphans found.
2. Ensure the ``export`` schema exists (idempotent CREATE SCHEMA IF NOT EXISTS;
   the infra runbook also creates it with the role grant, but we guard here
   for dev convenience).
3. ALTER TABLE public.exports SET SCHEMA export.

Downgrade
---------
ALTER TABLE export.exports SET SCHEMA public.

Post-upgrade state
------------------
- ``export.exports`` exists (table in schema ``export``).
- ``public.exports`` does NOT exist.
- ``export.alembic_version`` row tracks this migration (version_table_schema=
  "export" in env.py).
- The monolith's ``public.alembic_version`` row is UNCHANGED (head
  f31c75438e61).

Revision ID: e7a3c1f9b42d
Revises: (none — root of svc-export chain)
Create Date: 2026-06-12 00:00:00.000000
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "e7a3c1f9b42d"
down_revision: Union[str, None] = None  # root of the svc-export chain
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOG = logging.getLogger("alembic.runtime.migration")

_SCAN_SQL = sa.text(
    """
    SELECT COUNT(*) AS orphan_count
    FROM public.exports e
    WHERE NOT EXISTS (
        SELECT 1
        FROM public.users u
        WHERE u.id = e.user_id
    )
    """
)

_ORPHAN_DETAIL_SQL = sa.text(
    """
    SELECT e.id, e.user_id
    FROM public.exports e
    WHERE NOT EXISTS (
        SELECT 1
        FROM public.users u
        WHERE u.id = e.user_id
    )
    LIMIT 20
    """
)

# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Move public.exports → export.exports.

    Step 1: Risk#5 integrity pre-scan (online mode only; skipped in --sql offline render).
    Step 2: Ensure export schema exists.
    Step 3: ALTER TABLE exports SET SCHEMA export.
    """
    # ------------------------------------------------------------------
    # Step 1 — Risk#5 integrity pre-scan (spec §3.C / SUB_PLAN_01 §6)
    # In offline (--sql) mode there is no live DB connection; skip the
    # live query and log the scan SQL as a manual instruction.
    # ------------------------------------------------------------------
    if context.is_offline_mode():
        # Offline mode: emit the scan SQL to the log so operators can run
        # it manually before applying the generated SQL script.
        _LOG.info(
            "[svc-export migration e7a3c1f9b42d] OFFLINE MODE — "
            "Risk#5 scan SQL must be run manually before applying this migration:\n"
            "SELECT COUNT(*) AS orphan_count FROM public.exports e "
            "WHERE NOT EXISTS (SELECT 1 FROM public.users u WHERE u.id = e.user_id);"
        )
    else:
        conn = op.get_bind()
        _LOG.info(
            "[svc-export migration e7a3c1f9b42d] Risk#5 pre-scan: "
            "checking exports.user_id referential integrity ..."
        )

        row = conn.execute(_SCAN_SQL).fetchone()
        orphan_count: int = row[0] if row is not None else 0

        _LOG.info(
            "[svc-export migration e7a3c1f9b42d] Risk#5 pre-scan result: "
            "%d orphaned exports.user_id row(s) found.",
            orphan_count,
        )

        if orphan_count > 0:
            # Emit detail rows (up to 20) into the migration log for forensics.
            detail_rows = conn.execute(_ORPHAN_DETAIL_SQL).fetchall()
            for detail in detail_rows:
                _LOG.error(
                    "[svc-export migration e7a3c1f9b42d] Orphan row — "
                    "export.id=%s user_id=%s (no matching users row)",
                    detail[0],
                    detail[1],
                )
            raise RuntimeError(
                f"[svc-export migration e7a3c1f9b42d] ABORT: Risk#5 integrity pre-scan found "
                f"{orphan_count} orphaned exports.user_id row(s) with no matching "
                f"public.users row. Resolve the data integrity issue before re-running "
                f"this migration. Up to 20 offending rows have been emitted to the "
                f"migration log above."
            )

        _LOG.info("[svc-export migration e7a3c1f9b42d] Risk#5 pre-scan PASSED — zero orphans.")

    # ------------------------------------------------------------------
    # Step 2 — Ensure export schema exists
    # (Idempotent guard; infra runbook also creates it with role grant)
    # ------------------------------------------------------------------
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS export"))
    _LOG.info("[svc-export migration e7a3c1f9b42d] Schema 'export' ensured.")

    # ------------------------------------------------------------------
    # Step 3 — Move table to export schema
    # ------------------------------------------------------------------
    op.execute(sa.text("ALTER TABLE public.exports SET SCHEMA export"))
    _LOG.info("[svc-export migration e7a3c1f9b42d] public.exports moved to export.exports.")


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Move export.exports back to public schema.

    This is the §3.C tested downgrade (SET SCHEMA public).
    No integrity scan needed on downgrade — we are restoring to the original
    layout which already had the FK to public.users.
    """
    op.execute(sa.text("ALTER TABLE export.exports SET SCHEMA public"))
    _LOG.info(
        "[svc-export migration e7a3c1f9b42d] "
        "export.exports moved back to public.exports (downgrade)."
    )
