"""Move users table from public to iam schema + drop 6 cross-schema FKs.

This is the first (and root) migration in the svc-iam standalone Alembic chain.
It is ENTIRELY SEPARATE from the monolith chain (head f31c75438e61).

Background
----------
MASTER_PLAN §2.D assigns the ``users`` table to Postgres schema ``iam``
as part of the V1.5 schema-per-service isolation strategy.  This migration
effects that move (SUB_PLAN_0G §0.7 + spec_msG_backend.md §3.D).

``users`` is FK-referenced by 6 tables across 5 schemas.  After ``users``
leaves ``public``, any surviving FK constraint that points at
``public.users`` becomes a dangling cross-schema FK.  MASTER_PLAN §2.D
locked policy: drop these FKs at iam-extraction time; application-layer
``assert_owned`` / ``scope_to_user`` is the replacement referential defence.
(CI Contract 8 ``check_scope_to_user.py`` enforces this at the code level.)

The DROP set: 6 FKs across 5 schemas (§0.7 table)
----------------------------------------------------
+---+-----------------------------------+-------------------------------------+
| # | FK constraint name                | Table                               |
+---+-----------------------------------+-------------------------------------+
| 1 | audit_events_user_id_fkey         | public.audit_events                 |
| 2 | fk_seller_profile_user_id         | public.seller_profile               |
| 3 | catalogs_user_id_fkey             | public.catalogs                     |
| 4 | products_user_id_fkey             | public.products                     |
| 5 | exports_user_id_fkey              | public.exports (or export.exports)  |
| 6 | fk_product_drafts_user_id         | public.product_drafts               |
+---+-----------------------------------+-------------------------------------+

NOTE on sibling ownership (§0.7 annotation):
- FK #2 (seller_profile) may have been dropped by the customer extraction
  (MS-3, SUB_PLAN_0E) which runs BEFORE iam (MS-4).
- FK #5 (exports) may have been dropped by the export extraction (MS-1,
  SUB_PLAN_01) which runs BEFORE iam.
- FKs #1/#3/#4/#6 belong to tables still in public at MS-4 time (audit_events,
  catalogs, products, product_drafts — catalog is MS-5, the last extraction).
- pricing_calcs and product_images have NO user_id FK (verified §0.7).

CRITICAL: The migration drops EXACTLY the residual cross-schema FKs that are
ACTUALLY PRESENT in pg_constraint at upgrade time.  It cross-checks the live
constraint set before dropping — never assumes all 6 are present (sibling waves
may have already dropped some).

Risk #5 integrity pre-scan
--------------------------
Before any FK drop or schema move, we verify that every user_id column in every
FK-referencing table resolves to a real ``public.users`` row.  If orphans exist,
the migration raises and aborts — data integrity must be resolved first.

The scan checks all 6 potentially-referencing tables, but gracefully skips
any table that does not exist (e.g. ``export.exports`` if the svc-export
migration has already run on this DB, or ``seller_profile`` if customer-svc
has removed it from public).

Upgrade sequence
----------------
1. Risk#5 integrity pre-scan (all user_id-referencing tables).
2. Cross-check live pg_constraint: which of the 6 FKs are still present?
3. DROP each residual FK (exactly those found in step 2).
4. Ensure iam schema exists (idempotent — infra runbook also creates it).
5. ALTER TABLE public.users SET SCHEMA iam.

Downgrade sequence
------------------
1. ALTER TABLE iam.users SET SCHEMA public.
2. RESTORE each of the 6 FKs (idempotent — use ALTER TABLE ... ADD CONSTRAINT
   IF NOT EXISTS equivalent: drop+recreate or use DO$$ block to check).

Post-upgrade state
------------------
- ``iam.users`` exists (table in schema ``iam``).
- ``public.users`` does NOT exist.
- ``iam.alembic_version`` row tracks this migration (version_table_schema=
  "iam" in env.py).
- The monolith's ``public.alembic_version`` row is UNCHANGED (head f31c75438e61).
- 6 (or fewer) cross-schema FKs dropped from pg_constraint.

Live pg_constraint scan result at dev time (meesell_msg_test, 2026-06-13)
--------------------------------------------------------------------------
All 6 FKs present on a fresh monolith schema before any sibling migration runs:
  audit_events_user_id_fkey  | audit_events  | users
  catalogs_user_id_fkey      | catalogs      | users
  exports_user_id_fkey       | exports       | users
  fk_product_drafts_user_id  | product_drafts| users
  fk_seller_profile_user_id  | seller_profile| users
  products_user_id_fkey      | products      | users

Revision ID: b1c2d3e4f5a6
Revises: (none — root of svc-iam chain)
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

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = None  # root of the svc-iam chain
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOG = logging.getLogger("alembic.runtime.migration")

# The complete §0.7 FK set.  Each entry:
#   (constraint_name, table_name, table_schema)
# The live pg_constraint scan at upgrade time decides which are still present.
# table_schema is the CURRENT schema of the referencing table at MS-4 time.
# Notes:
#   - exports may be in schema 'export' if svc-export migration ran first;
#     we try both qualified names.
#   - seller_profile may already have FK dropped by customer extraction.
_ALL_FK_SPECS: list[tuple[str, str, str]] = [
    # (constraint_name, table_name, column_for_fk_restore)
    ("audit_events_user_id_fkey", "audit_events", "public"),
    ("fk_seller_profile_user_id", "seller_profile", "public"),
    ("catalogs_user_id_fkey", "catalogs", "public"),
    ("products_user_id_fkey", "products", "public"),
    ("exports_user_id_fkey", "exports", "public"),
    ("fk_product_drafts_user_id", "product_drafts", "public"),
]

# For the restore (downgrade), we need the FK definitions.
# These mirror the baseline migration 935e55b4852c exactly.
_FK_RESTORE_SPECS: dict[str, dict] = {
    "audit_events_user_id_fkey": {
        "table": "audit_events",
        "schema": "public",
        "column": "user_id",
        "ondelete": "RESTRICT",
    },
    "fk_seller_profile_user_id": {
        "table": "seller_profile",
        "schema": "public",
        "column": "user_id",
        "ondelete": "CASCADE",
    },
    "catalogs_user_id_fkey": {
        "table": "catalogs",
        "schema": "public",
        "column": "user_id",
        "ondelete": "CASCADE",
    },
    "products_user_id_fkey": {
        "table": "products",
        "schema": "public",
        "column": "user_id",
        "ondelete": "RESTRICT",
    },
    "exports_user_id_fkey": {
        "table": "exports",
        "schema": "public",
        "column": "user_id",
        "ondelete": "RESTRICT",
    },
    "fk_product_drafts_user_id": {
        "table": "product_drafts",
        "schema": "public",
        "column": "user_id",
        "ondelete": "CASCADE",
    },
}

# Tables that carry a user_id column referencing users.
# Checked in the Risk#5 pre-scan.  We try multiple schemas for tables that
# may have moved (exports may be in 'export' schema after MS-1).
_SCAN_TABLES: list[tuple[str, str]] = [
    ("audit_events", "public"),
    ("seller_profile", "public"),
    ("catalogs", "public"),
    ("products", "public"),
    ("exports", "public"),
    ("exports", "export"),       # in case svc-export migration already ran
    ("product_drafts", "public"),
]

# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------


def _table_exists(conn: sa.engine.Connection, schema: str, table: str) -> bool:
    """Return True if the given schema.table exists."""
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = :schema AND table_name = :table)"
        ),
        {"schema": schema, "table": table},
    )
    row = result.fetchone()
    return bool(row[0]) if row else False


def _constraint_exists(conn: sa.engine.Connection, conname: str) -> bool:
    """Return True if a FK constraint with the given name exists anywhere in pg_constraint."""
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM pg_constraint "
            "WHERE conname = :conname AND contype = 'f'"
            ")"
        ),
        {"conname": conname},
    )
    row = result.fetchone()
    return bool(row[0]) if row else False


def _get_residual_fks(conn: sa.engine.Connection) -> list[str]:
    """Return the names of cross-schema user.id FKs still present in pg_constraint.

    Queries pg_constraint directly (the authoritative source — recipe §0.7 law).
    Only returns FKs that are in our known set; never drops unexpected constraints.
    """
    result = conn.execute(
        sa.text(
            "SELECT conname "
            "FROM pg_constraint "
            "WHERE confrelid = 'public.users'::regclass "
            "AND contype = 'f' "
            "AND conname = ANY(:names)"
        ),
        {"names": [spec[0] for spec in _ALL_FK_SPECS]},
    )
    return [row[0] for row in result.fetchall()]


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Move public.users to iam schema after dropping residual cross-schema FKs.

    Step 1: Risk#5 integrity pre-scan — every user_id in every referencing
            table resolves to a real public.users row.
    Step 2: pg_constraint cross-check — which of the 6 FKs are still present?
    Step 3: DROP each residual FK.
    Step 4: Ensure iam schema exists.
    Step 5: ALTER TABLE public.users SET SCHEMA iam.
    """
    if context.is_offline_mode():
        _LOG.info(
            "[svc-iam b1c2d3e4f5a6] OFFLINE MODE — Risk#5 scan SQL must be "
            "run manually before applying this migration.  See migration docstring "
            "for the full scan query.  Then apply: "
            "ALTER TABLE public.users SET SCHEMA iam;"
        )
        # In offline mode, emit the DDL Alembic can generate without a live conn.
        op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS iam"))
        op.execute(sa.text("ALTER TABLE public.users SET SCHEMA iam"))
        return

    conn = op.get_bind()

    # ------------------------------------------------------------------
    # Step 1 — Risk#5 integrity pre-scan
    # Check every table that carries a user_id referencing users.id.
    # We check all candidate tables, skipping ones that don't exist
    # (e.g. exports in 'export' schema if svc-export migration ran first,
    # or seller_profile already dropped by customer migration).
    # ------------------------------------------------------------------
    _LOG.info(
        "[svc-iam b1c2d3e4f5a6] Risk#5 pre-scan: "
        "checking user_id referential integrity across all referencing tables..."
    )
    total_orphans = 0
    scanned_tables: list[str] = []

    for table_name, schema_name in _SCAN_TABLES:
        if not _table_exists(conn, schema_name, table_name):
            _LOG.info(
                "[svc-iam b1c2d3e4f5a6] Risk#5 scan: %s.%s does not exist — skipped.",
                schema_name,
                table_name,
            )
            continue

        qualified = f"{schema_name}.{table_name}"
        scan_sql = sa.text(
            f"SELECT COUNT(*) AS orphan_count "
            f"FROM {qualified} t "
            f"WHERE t.user_id IS NOT NULL "
            f"AND NOT EXISTS ("
            f"SELECT 1 FROM public.users u WHERE u.id = t.user_id"
            f")"
        )
        row = conn.execute(scan_sql).fetchone()
        orphan_count: int = row[0] if row is not None else 0

        _LOG.info(
            "[svc-iam b1c2d3e4f5a6] Risk#5 scan: %s — %d orphaned user_id row(s).",
            qualified,
            orphan_count,
        )
        scanned_tables.append(qualified)

        if orphan_count > 0:
            total_orphans += orphan_count
            # Emit up to 20 detail rows for forensics.
            detail_sql = sa.text(
                f"SELECT id, user_id FROM {qualified} "
                f"WHERE user_id IS NOT NULL "
                f"AND NOT EXISTS ("
                f"SELECT 1 FROM public.users u WHERE u.id = user_id"
                f") LIMIT 20"
            )
            try:
                detail_rows = conn.execute(detail_sql).fetchall()
                for detail in detail_rows:
                    _LOG.error(
                        "[svc-iam b1c2d3e4f5a6] Orphan in %s — id=%s user_id=%s",
                        qualified,
                        detail[0],
                        detail[1],
                    )
            except Exception:
                _LOG.warning(
                    "[svc-iam b1c2d3e4f5a6] Could not fetch detail rows for %s "
                    "(no 'id' column?); count=%d",
                    qualified,
                    orphan_count,
                )

    if total_orphans > 0:
        raise RuntimeError(
            f"[svc-iam b1c2d3e4f5a6] ABORT: Risk#5 integrity pre-scan found "
            f"{total_orphans} orphaned user_id row(s) across tables: "
            f"{scanned_tables}.  Resolve the data integrity issue before "
            f"re-running this migration.  Offending rows have been emitted to "
            f"the migration log above."
        )

    _LOG.info(
        "[svc-iam b1c2d3e4f5a6] Risk#5 pre-scan PASSED — zero orphans across %d table(s): %s",
        len(scanned_tables),
        scanned_tables,
    )

    # ------------------------------------------------------------------
    # Step 2 — pg_constraint cross-check: which FKs are still present?
    # Waves MS-2/MS-3 may have already dropped some of the 6 FKs.
    # We drop EXACTLY the residual set — neither more nor less.
    # ------------------------------------------------------------------
    residual_fks = _get_residual_fks(conn)
    _LOG.info(
        "[svc-iam b1c2d3e4f5a6] pg_constraint cross-check result: "
        "%d residual FK(s) referencing public.users: %s",
        len(residual_fks),
        residual_fks,
    )

    # ------------------------------------------------------------------
    # Step 3 — DROP each residual FK
    # ------------------------------------------------------------------
    for fk_name in residual_fks:
        spec = _FK_RESTORE_SPECS.get(fk_name)
        if spec is None:
            _LOG.warning(
                "[svc-iam b1c2d3e4f5a6] FK '%s' found in pg_constraint but "
                "not in our known set — skipping to avoid unexpected drops.",
                fk_name,
            )
            continue
        qualified_table = f"{spec['schema']}.{spec['table']}"
        drop_sql = sa.text(
            f"ALTER TABLE {qualified_table} "
            f"DROP CONSTRAINT IF EXISTS {fk_name}"
        )
        conn.execute(drop_sql)
        _LOG.info(
            "[svc-iam b1c2d3e4f5a6] Dropped FK '%s' on %s.user_id → public.users.",
            fk_name,
            qualified_table,
        )

    # ------------------------------------------------------------------
    # Step 4 — Ensure iam schema exists
    # (Idempotent guard; infra runbook also creates it with role grant)
    # The schema was already created by do_run_migrations() in env.py
    # before context.configure(), but we guard here too for explicitness.
    # ------------------------------------------------------------------
    conn.execute(sa.text("CREATE SCHEMA IF NOT EXISTS iam"))
    _LOG.info("[svc-iam b1c2d3e4f5a6] Schema 'iam' ensured.")

    # ------------------------------------------------------------------
    # Step 5 — Move users table to iam schema
    # ------------------------------------------------------------------
    conn.execute(sa.text("ALTER TABLE public.users SET SCHEMA iam"))
    _LOG.info(
        "[svc-iam b1c2d3e4f5a6] public.users moved to iam.users. "
        "Dropped %d FK(s): %s",
        len(residual_fks),
        residual_fks,
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Move iam.users back to public schema and restore the 6 cross-schema FKs.

    Downgrade sequence:
    1. ALTER TABLE iam.users SET SCHEMA public  (restores the table).
    2. RESTORE each FK using IF NOT EXISTS semantics
       (uses DO$$ block to check pg_constraint before adding).

    The FK definitions are taken verbatim from the baseline migration
    935e55b4852c so they are byte-identical to the original schema.
    """
    if context.is_offline_mode():
        _LOG.info(
            "[svc-iam b1c2d3e4f5a6] OFFLINE DOWNGRADE: "
            "ALTER TABLE iam.users SET SCHEMA public; "
            "then restore the 6 FK constraints manually."
        )
        op.execute(sa.text("ALTER TABLE iam.users SET SCHEMA public"))
        return

    conn = op.get_bind()

    # ------------------------------------------------------------------
    # Step 1 — Move users back to public
    # ------------------------------------------------------------------
    conn.execute(sa.text("ALTER TABLE iam.users SET SCHEMA public"))
    _LOG.info("[svc-iam b1c2d3e4f5a6] DOWNGRADE: iam.users moved back to public.users.")

    # ------------------------------------------------------------------
    # Step 2 — Restore each FK (idempotent: skip if already present)
    # FK definitions are verbatim from baseline migration 935e55b4852c.
    # ------------------------------------------------------------------
    fk_restore_ddl: list[tuple[str, str]] = [
        (
            "audit_events_user_id_fkey",
            "ALTER TABLE public.audit_events "
            "ADD CONSTRAINT audit_events_user_id_fkey "
            "FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE RESTRICT",
        ),
        (
            "fk_seller_profile_user_id",
            "ALTER TABLE public.seller_profile "
            "ADD CONSTRAINT fk_seller_profile_user_id "
            "FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE",
        ),
        (
            "catalogs_user_id_fkey",
            "ALTER TABLE public.catalogs "
            "ADD CONSTRAINT catalogs_user_id_fkey "
            "FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE",
        ),
        (
            "products_user_id_fkey",
            "ALTER TABLE public.products "
            "ADD CONSTRAINT products_user_id_fkey "
            "FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE RESTRICT",
        ),
        (
            "exports_user_id_fkey",
            "ALTER TABLE public.exports "
            "ADD CONSTRAINT exports_user_id_fkey "
            "FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE RESTRICT",
        ),
        (
            "fk_product_drafts_user_id",
            "ALTER TABLE public.product_drafts "
            "ADD CONSTRAINT fk_product_drafts_user_id "
            "FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE",
        ),
    ]

    for conname, ddl in fk_restore_ddl:
        # Check if FK already exists (idempotent restore).
        exists_result = conn.execute(
            sa.text(
                "SELECT EXISTS ("
                "SELECT 1 FROM pg_constraint "
                "WHERE conname = :conname AND contype = 'f'"
                ")"
            ),
            {"conname": conname},
        )
        exists_row = exists_result.fetchone()
        already_exists = bool(exists_row[0]) if exists_row else False

        if already_exists:
            _LOG.info(
                "[svc-iam b1c2d3e4f5a6] DOWNGRADE: FK '%s' already exists — skip restore.",
                conname,
            )
            continue

        # Check that the referencing table exists in public (some may be in
        # another schema after their own service extraction).
        spec = _FK_RESTORE_SPECS.get(conname)
        if spec and not _table_exists(conn, spec["schema"], spec["table"]):
            _LOG.warning(
                "[svc-iam b1c2d3e4f5a6] DOWNGRADE: Table '%s.%s' does not exist — "
                "cannot restore FK '%s'. This is expected if the referencing table's "
                "service extraction also moved it out of public.",
                spec["schema"],
                spec["table"],
                conname,
            )
            continue

        conn.execute(sa.text(ddl))
        _LOG.info(
            "[svc-iam b1c2d3e4f5a6] DOWNGRADE: Restored FK '%s'.",
            conname,
        )

    _LOG.info(
        "[svc-iam b1c2d3e4f5a6] DOWNGRADE complete: public.users restored + FKs restored."
    )
