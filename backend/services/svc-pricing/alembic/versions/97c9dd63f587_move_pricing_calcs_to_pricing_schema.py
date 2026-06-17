"""Move pricing_calcs table from public schema to pricing schema.

This is the first (and currently only) migration in the svc-pricing standalone
Alembic chain.  It is SEPARATE from the monolith chain (head f31c75438e61).

Context
-------
MASTER_PLAN §2.D assigns the ``pricing_calcs`` table to Postgres schema
``pricing`` as part of the V1.5 schema-per-service isolation strategy.  This
migration effects that move.  The monolith's ``public.pricing_calcs`` is moved;
the monolith's Alembic chain is NOT touched.

The migration is authored per spec §3.C (database-builder dispatch) from
backend-coordinator spec_msD_backend.md.

Cross-schema FK invariant (CRITICAL — spec §3.C)
-------------------------------------------------
``pricing_calcs.product_id → public.products.id`` (FK constraint
``pricing_calcs_product_id_fkey``) is NOT dropped here.  Catalog is MS-5
(still in-process at MS-3).  The FK is dropped at catalog extraction (MS-H),
NOT at pricing extraction.  PostgreSQL cross-schema FKs are fully legal and
are maintained transparently across schema moves — the FK constraint remains
valid after ``ALTER TABLE pricing_calcs SET SCHEMA pricing``.

Source of FK: backend/app/shared/models/pricing_calc.py line 42-44
  ``ForeignKey("products.id", ondelete="CASCADE")``
  Table name verified: __tablename__ = "pricing_calcs" (pricing_calc.py line 33)

Risk #5 integrity pre-scan (spec §3.C)
---------------------------------------
Before the schema move we verify that every ``pricing_calcs.product_id``
resolves to a real row in ``public.products``.  The FK is declared CASCADE
in the ORM model (pricing_calc.py:42-44), so orphans should not exist in a
healthy database, but we guard here to abort cleanly if data integrity is
compromised.

If orphaned rows are found the migration logs them and raises, aborting the
transaction cleanly.  Do NOT proceed with the schema move if orphans exist —
they indicate a data integrity problem that must be resolved manually before
extraction.

Upgrade
-------
1. Risk#5 scan: SELECT count of pricing_calcs rows whose product_id has no
   match in products.  Raise if orphans found; emit up to 20 detail rows.
2. Ensure the ``pricing`` schema exists (idempotent CREATE SCHEMA IF NOT EXISTS;
   the infra runbook also creates it with the role grant, but we guard here
   for dev convenience).
3. ALTER TABLE public.pricing_calcs SET SCHEMA pricing.

Downgrade
---------
ALTER TABLE pricing.pricing_calcs SET SCHEMA public.

Post-upgrade state
------------------
- ``pricing.pricing_calcs`` exists (table in schema ``pricing``).
- ``public.pricing_calcs`` does NOT exist.
- ``pricing.alembic_version`` row tracks this migration (version_table_schema=
  "pricing" in env.py).
- The monolith's ``public.alembic_version`` row is UNCHANGED (head
  f31c75438e61).
- The FK ``pricing_calcs.product_id → public.products.id`` remains VALID
  (cross-schema FK, not dropped until MS-H catalog extraction).

Revision ID: 97c9dd63f587
Revises: (none — root of svc-pricing chain)
Create Date: 2026-06-13 00:00:00.000000
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "97c9dd63f587"
down_revision: Union[str, None] = None  # root of the svc-pricing chain
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOG = logging.getLogger("alembic.runtime.migration")

# Risk#5 pre-scan: count pricing_calcs rows whose product_id has no match in
# products.  The FK is declared CASCADE (pricing_calc.py:42-44) so this
# should always be zero on a healthy database.
_SCAN_SQL = sa.text(
    """
    SELECT COUNT(*) AS orphan_count
    FROM public.pricing_calcs pc
    WHERE NOT EXISTS (
        SELECT 1
        FROM public.products p
        WHERE p.id = pc.product_id
    )
    """
)

_ORPHAN_DETAIL_SQL = sa.text(
    """
    SELECT pc.id, pc.product_id
    FROM public.pricing_calcs pc
    WHERE NOT EXISTS (
        SELECT 1
        FROM public.products p
        WHERE p.id = pc.product_id
    )
    LIMIT 20
    """
)

# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Move public.pricing_calcs → pricing.pricing_calcs.

    Step 1: Risk#5 integrity pre-scan (online mode only; skipped in --sql offline render).
    Step 2: Ensure pricing schema exists.
    Step 3: ALTER TABLE pricing_calcs SET SCHEMA pricing.

    CRITICAL: The FK pricing_calcs.product_id → public.products.id is NOT
    dropped here.  It remains valid as a cross-schema FK.  It will be dropped
    at MS-H (catalog extraction), not here.
    """
    # ------------------------------------------------------------------
    # Step 1 — Risk#5 integrity pre-scan (spec §3.C)
    # In offline (--sql) mode there is no live DB connection; skip the
    # live query and log the scan SQL as a manual instruction.
    # ------------------------------------------------------------------
    if context.is_offline_mode():
        _LOG.info(
            "[svc-pricing migration 97c9dd63f587] OFFLINE MODE — "
            "Risk#5 scan SQL must be run manually before applying this migration:\n"
            "SELECT COUNT(*) AS orphan_count FROM public.pricing_calcs pc "
            "WHERE NOT EXISTS (SELECT 1 FROM public.products p WHERE p.id = pc.product_id);"
        )
    else:
        conn = op.get_bind()
        _LOG.info(
            "[svc-pricing migration 97c9dd63f587] Risk#5 pre-scan: "
            "checking pricing_calcs.product_id referential integrity ..."
        )

        row = conn.execute(_SCAN_SQL).fetchone()
        orphan_count: int = row[0] if row is not None else 0

        _LOG.info(
            "[svc-pricing migration 97c9dd63f587] Risk#5 pre-scan result: "
            "%d orphaned pricing_calcs.product_id row(s) found.",
            orphan_count,
        )

        if orphan_count > 0:
            # Emit detail rows (up to 20) into the migration log for forensics.
            detail_rows = conn.execute(_ORPHAN_DETAIL_SQL).fetchall()
            for detail in detail_rows:
                _LOG.error(
                    "[svc-pricing migration 97c9dd63f587] Orphan row — "
                    "pricing_calc.id=%s product_id=%s (no matching products row)",
                    detail[0],
                    detail[1],
                )
            raise RuntimeError(
                f"[svc-pricing migration 97c9dd63f587] ABORT: Risk#5 integrity pre-scan found "
                f"{orphan_count} orphaned pricing_calcs.product_id row(s) with no matching "
                f"public.products row. Resolve the data integrity issue before re-running "
                f"this migration. Up to 20 offending rows have been emitted to the "
                f"migration log above."
            )

        _LOG.info("[svc-pricing migration 97c9dd63f587] Risk#5 pre-scan PASSED — zero orphans.")

    # ------------------------------------------------------------------
    # Step 2 — Ensure pricing schema exists
    # (Idempotent guard; infra runbook also creates it with role grant)
    # ------------------------------------------------------------------
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS pricing"))
    _LOG.info("[svc-pricing migration 97c9dd63f587] Schema 'pricing' ensured.")

    # ------------------------------------------------------------------
    # Step 3 — Move table to pricing schema
    # The FK pricing_calcs.product_id → public.products.id remains valid
    # as a cross-schema FK.  PostgreSQL preserves FK constraints across
    # schema moves.  This FK is NOT dropped here (spec §3.C).
    # ------------------------------------------------------------------
    op.execute(sa.text("ALTER TABLE public.pricing_calcs SET SCHEMA pricing"))
    _LOG.info(
        "[svc-pricing migration 97c9dd63f587] "
        "public.pricing_calcs moved to pricing.pricing_calcs. "
        "Cross-schema FK pricing_calcs.product_id → public.products.id preserved."
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Move pricing.pricing_calcs back to public schema.

    This is the §3.C tested downgrade (SET SCHEMA public).
    No integrity scan needed on downgrade — we are restoring to the original
    layout which already had the FK to public.products.
    """
    op.execute(sa.text("ALTER TABLE pricing.pricing_calcs SET SCHEMA public"))
    _LOG.info(
        "[svc-pricing migration 97c9dd63f587] "
        "pricing.pricing_calcs moved back to public.pricing_calcs (downgrade)."
    )
