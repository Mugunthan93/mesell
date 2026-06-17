"""Move 3 tenant-scoped catalog tables from public schema to catalog schema.

This is the first (and root) migration in the svc-catalog standalone Alembic
chain.  It is ENTIRELY SEPARATE from the monolith chain (head f31c75438e61).

Context
-------
MASTER_PLAN §2.D assigns the 3 TENANT-SCOPED catalog tables to Postgres schema
``catalog`` as part of the V1.5 schema-per-service isolation strategy.
SUB_PLAN_0H_catalog_extraction.md §DB-tables-owned confirms the 3 tables.
Catalog is THE SPINE (MS-5, LAST + RISKIEST extraction — runs ALONE).

Verified from AS-BUILT source (file:line, SOURCE WINS per recipe §0):
  - ``catalogs``       — backend/app/shared/models/catalog.py:33 __tablename__
  - ``products``       — backend/app/shared/models/product.py:41 __tablename__
  - ``product_drafts`` — backend/app/shared/models/product_draft.py:38 __tablename__
  ORM imports cited at repository.py:59-61 (Catalog, Product, ProductDraft).

All 3 tables are FULLY TENANT-SCOPED — scope_to_user() on every product/catalog
read (repository.py:87,:108,:126,:143).  Moving them together preserves the
intra-service FK relationship (products.catalog_id → catalogs).

Cross-schema FK handling (THE SPINE — complex FK surface)
---------------------------------------------------------
After the schema move, the following cross-schema FK relationships arise:

INTRA-CATALOG-SCHEMA FKs (both sides in catalog schema — intra-schema, fully valid):
  catalog.products.catalog_id     → catalog.catalogs.id          (CASCADE DELETE)
  catalog.product_drafts.product_id → catalog.products.id        (CASCADE DELETE)

CROSS-SCHEMA FKs (catalog schema → other schemas — valid in PostgreSQL, preserved):
  catalog.catalogs.user_id        → public.users.id   (→ iam.users post #220)
  catalog.catalogs.category_id    → public.categories.id (→ category.categories post #221)
  catalog.products.user_id        → public.users.id   (→ iam.users post #220)
  catalog.products.category_id    → public.categories.id (→ category.categories post #221)
  catalog.product_drafts.user_id  → public.users.id   (→ iam.users post #220)

CATALOG DROPS NO FKs in this migration.  The existing FK constraints on all
5 columns survive as cross-schema references.  PostgreSQL supports cross-schema
FKs within the same database — the FK objects remain valid after SET SCHEMA.

IMPORTANT: Once iam PR #220 merges (ALTER users SET SCHEMA iam + drops FKs
#3 catalogs_user_id_fkey, #4 products_user_id_fkey, #6 fk_product_drafts_user_id),
those FKs will have been removed from pg_constraint.  Similarly, after category
PR #221 merges (moves categories to category schema), the catalogs.category_id
and products.category_id FKs become cross-schema but remain intact at the PG level.
This migration composes cleanly with both because SET SCHEMA on our tables is
orthogonal to FK drops on the user side.

Index preservation (verified from ORM __table_args__)
-----------------------------------------------------
PostgreSQL ALTER TABLE ... SET SCHEMA preserves ALL indexes intact.
Preserved on catalogs:
  idx_catalogs_user            (btree on user_id)
  idx_catalogs_user_created    (btree on user_id, created_at)
  idx_catalogs_category_id     (btree on category_id)
Preserved on products:
  idx_products_user            (btree on user_id)
  idx_products_category        (btree on category_id)
  idx_products_status          (btree on status)
  idx_products_user_status     (btree on user_id, status)
  idx_products_catalog_id      (btree on catalog_id)
Preserved on product_drafts:
  idx_product_drafts_product_id  (btree on product_id)
  idx_product_drafts_saved_at    (btree on saved_at — G10 migration f31c75438e61)

FK constraint objects are also preserved by SET SCHEMA (PG preserves all
constraint objects on the table; cross-schema references just resolve to the
new qualified name internally).

Risk #5 / Risk #6 integrity pre-scan (products.user_id → users)
----------------------------------------------------------------
Before the schema move, we verify that every products.user_id value resolves
to a real public.users row.  This is the §6 Risk #5 pattern
(SUB_PLAN_0H R6 — cross-schema FK integrity).
We also scan catalogs.user_id and product_drafts.user_id for completeness.

At the develop baseline (ebb700e) on which this migration is built:
  - public.users exists (iam #220 is OPEN BUT UNMERGED)
  - public.catalogs, public.products, public.product_drafts are in public

Merge ordering note for the founder
------------------------------------
SAFE MERGE ORDER (and WHY):

  1. Merge iam PR #220  — ALTER users SET SCHEMA iam; drops FK constraints
     #3 (catalogs_user_id_fkey), #4 (products_user_id_fkey),
     #6 (fk_product_drafts_user_id).  After this, the 3 FK objects on catalog
     tables pointing at users.id are gone from pg_constraint.
     The catalog tables remain in public at this point.

  2. Merge category PR #221 — Moves categories/templates/field_enum_values/
     field_aliases to schema category.  After this, catalogs.category_id and
     products.category_id FK constraints reference category.categories (cross-
     schema, still valid in PG).  The catalog tables remain in public.

  3. Merge catalog MS-5 PR (this migration) — Moves catalogs, products,
     product_drafts to schema catalog via ALTER TABLE ... SET SCHEMA catalog.
     At this point the FK constraint objects on category_id may remain as
     cross-schema FKs (catalog → category) OR may have been resolved by the
     category wave — either way the SET SCHEMA on our 3 tables is safe.
     NO FK drops are performed by this migration.

ANTI-PATTERN (must NOT do):
  - Merging catalog MS-5 BEFORE iam #220: the user FK objects are still live
    and will point at (now-invalid) public.users after iam moves users.
    However, iam #220 drops these FKs itself, so the collision risk is only
    a sequencing window issue (both iam and catalog touch different tables).
    The SAFE order above eliminates any window.

Upgrade sequence
----------------
1. Risk#5 integrity pre-scan:
   - products.user_id must all resolve to real public.users rows
   - catalogs.user_id must all resolve to real public.users rows
   - product_drafts.user_id must all resolve to real public.users rows
   Raise RuntimeError on any orphan.
2. Ensure the ``catalog`` schema exists (idempotent guard).
3. ALTER TABLE public.catalogs SET SCHEMA catalog.
4. ALTER TABLE public.products SET SCHEMA catalog.
5. ALTER TABLE public.product_drafts SET SCHEMA catalog.

Downgrade sequence
------------------
Reverse in exactly the reverse order:
1. ALTER TABLE catalog.product_drafts SET SCHEMA public.
2. ALTER TABLE catalog.products SET SCHEMA public.
3. ALTER TABLE catalog.catalogs SET SCHEMA public.

Post-upgrade state
------------------
- ``catalog.catalogs``, ``catalog.products``, ``catalog.product_drafts``
  exist (tables in schema ``catalog``).
- The original ``public.*`` names for those 3 tables do NOT exist.
- ``catalog.alembic_version`` row tracks this migration (version_table_schema=
  "catalog" in env.py).
- The monolith's ``public.alembic_version`` row is UNCHANGED (head f31c75438e61).
- All btree indexes on all 3 tables survive intact (PostgreSQL preserves all
  indexes on ALTER TABLE ... SET SCHEMA).
- Cross-schema FK constraints pointing at users / categories survive intact
  (PostgreSQL preserves FK constraint objects on the moving table).

Revision ID: a8f3b2e9c1d5
Revises: (none — root of svc-catalog chain)
Create Date: 2026-06-14 00:00:00.000000
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "a8f3b2e9c1d5"
down_revision: Union[str, None] = None  # root of the svc-catalog chain
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOG = logging.getLogger("alembic.runtime.migration")

_MIGRATION_TAG = "[svc-catalog migration a8f3b2e9c1d5]"

# Risk#5 / Risk#6 orphan scan: verify every user_id in the 3 catalog-owned
# tenant-scoped tables resolves to a real public.users row.
# Note: product_drafts uses a NULLABLE check (user_id is PK — never null
# in practice, but the check is belt-and-suspenders).
# We scan public.users at upgrade time; iam #220 has NOT yet merged
# at the point this migration was authored (develop tip ebb700e).
_ORPHAN_SCANS: list[tuple[str, str, str]] = [
    # (table, schema, description)
    ("products", "public", "products.user_id → public.users.id"),
    ("catalogs", "public", "catalogs.user_id → public.users.id"),
    ("product_drafts", "public", "product_drafts.user_id → public.users.id"),
]


def _table_exists(conn: sa.engine.Connection, schema: str, table: str) -> bool:
    """Return True if the given schema.table exists in information_schema."""
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.tables "
            "  WHERE table_schema = :schema AND table_name = :table"
            ")"
        ),
        {"schema": schema, "table": table},
    )
    row = result.fetchone()
    return bool(row[0]) if row else False


def _users_table_schema(conn: sa.engine.Connection) -> str:
    """Detect which schema hosts the users table (public or iam).

    At develop tip the users table is in public (iam #220 is unmerged).
    If the founder merges iam #220 before running this migration, users
    will be in the iam schema.  We detect dynamically so the scan is
    correct regardless of merge order.
    """
    for schema in ("public", "iam"):
        if _table_exists(conn, schema, "users"):
            return schema
    raise RuntimeError(
        f"{_MIGRATION_TAG} ABORT: Could not locate 'users' table in either "
        f"'public' or 'iam' schema.  The database is in an unexpected state."
    )


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Move 3 tenant-scoped catalog tables from public schema to catalog schema.

    Step 1: Risk#5 integrity pre-scan — every user_id in every catalog-owned
            table resolves to a real users row (in public or iam schema,
            dynamically detected).
    Step 2: Ensure catalog schema exists (idempotent guard).
    Step 3: ALTER TABLE public.catalogs SET SCHEMA catalog.
    Step 4: ALTER TABLE public.products SET SCHEMA catalog.
    Step 5: ALTER TABLE public.product_drafts SET SCHEMA catalog.

    Index preservation: PostgreSQL ALTER TABLE ... SET SCHEMA preserves all
    indexes (btree) intact.  The 10 indexes on these 3 tables survive the
    schema move with their names and operator classes unchanged.

    FK constraint preservation: All FK constraint objects on the moving tables
    survive SET SCHEMA.  Cross-schema FKs (toward users / categories) remain
    in pg_constraint pointing at the resolved target (iam.users or
    category.categories after their respective extractions).  Catalog DROPS
    NO FKs in this migration per SUB_PLAN_0H decision (catalog drops no FK;
    the scoped FK lifecycle is owned by the referenced service's wave).
    """
    # ------------------------------------------------------------------
    # Step 1 — Risk#5 integrity pre-scan (online mode only)
    # ------------------------------------------------------------------
    if context.is_offline_mode():
        _LOG.info(
            "%s OFFLINE MODE — Risk#5 scan SQL must be run manually before "
            "applying this migration:\n"
            "SELECT COUNT(*) FROM public.products p "
            "WHERE NOT EXISTS (SELECT 1 FROM public.users u WHERE u.id = p.user_id);\n"
            "SELECT COUNT(*) FROM public.catalogs c "
            "WHERE NOT EXISTS (SELECT 1 FROM public.users u WHERE u.id = c.user_id);\n"
            "SELECT COUNT(*) FROM public.product_drafts pd "
            "WHERE NOT EXISTS (SELECT 1 FROM public.users u WHERE u.id = pd.user_id);",
            _MIGRATION_TAG,
        )
    else:
        conn = op.get_bind()

        # Dynamically detect which schema hosts users (public or iam).
        users_schema = _users_table_schema(conn)
        _LOG.info(
            "%s Risk#5 pre-scan: users table located in schema '%s'.",
            _MIGRATION_TAG,
            users_schema,
        )

        _LOG.info(
            "%s Risk#5 pre-scan: checking user_id referential integrity "
            "across all 3 catalog-owned tenant-scoped tables...",
            _MIGRATION_TAG,
        )

        total_orphans = 0

        for table_name, table_schema, description in _ORPHAN_SCANS:
            if not _table_exists(conn, table_schema, table_name):
                _LOG.info(
                    "%s Risk#5 scan: %s.%s does not exist — skipped.",
                    _MIGRATION_TAG,
                    table_schema,
                    table_name,
                )
                continue

            qualified = f"{table_schema}.{table_name}"
            users_qualified = f"{users_schema}.users"

            scan_sql = sa.text(
                f"SELECT COUNT(*) AS orphan_count "
                f"FROM {qualified} t "
                f"WHERE t.user_id IS NOT NULL "
                f"AND NOT EXISTS ("
                f"  SELECT 1 FROM {users_qualified} u WHERE u.id = t.user_id"
                f")"
            )
            row = conn.execute(scan_sql).fetchone()
            orphan_count: int = row[0] if row is not None else 0

            _LOG.info(
                "%s Risk#5 scan: %s (%s) — %d orphaned user_id row(s).",
                _MIGRATION_TAG,
                qualified,
                description,
                orphan_count,
            )

            if orphan_count > 0:
                total_orphans += orphan_count
                # Emit up to 20 detail rows for forensics.
                detail_sql = sa.text(
                    f"SELECT id, user_id FROM {qualified} "
                    f"WHERE user_id IS NOT NULL "
                    f"AND NOT EXISTS ("
                    f"  SELECT 1 FROM {users_qualified} u WHERE u.id = user_id"
                    f") LIMIT 20"
                )
                try:
                    detail_rows = conn.execute(detail_sql).fetchall()
                    for detail in detail_rows:
                        _LOG.error(
                            "%s Orphan row in %s — id=%s user_id=%s "
                            "(no matching %s row)",
                            _MIGRATION_TAG,
                            qualified,
                            detail[0],
                            detail[1],
                            users_qualified,
                        )
                except Exception:
                    _LOG.warning(
                        "%s Could not fetch orphan detail rows for %s (no 'id' col?).",
                        _MIGRATION_TAG,
                        qualified,
                    )

        if total_orphans > 0:
            raise RuntimeError(
                f"{_MIGRATION_TAG} ABORT: Risk#5 integrity pre-scan found "
                f"{total_orphans} orphaned user_id row(s) across catalog-owned "
                f"tables with no matching {users_schema}.users row.  Resolve the "
                f"data integrity issue before re-running this migration.  Up to 20 "
                f"offending rows per table have been emitted to the migration log."
            )

        _LOG.info(
            "%s Risk#5 pre-scan PASSED — zero orphans across all catalog-owned "
            "tenant-scoped tables.",
            _MIGRATION_TAG,
        )

    # ------------------------------------------------------------------
    # Step 2 — Ensure catalog schema exists (idempotent guard)
    # The env.py do_run_migrations() also issues this before configure().
    # Belt-and-suspenders: emit it here too so the schema exists when the
    # ALTER TABLE statements run inside the migration transaction.
    # ------------------------------------------------------------------
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS catalog"))
    _LOG.info("%s Schema 'catalog' ensured.", _MIGRATION_TAG)

    # ------------------------------------------------------------------
    # Step 3 — Move catalogs table
    # Preserves indexes: idx_catalogs_user, idx_catalogs_user_created,
    # idx_catalogs_category_id.
    # Preserves FKs: catalogs_user_id_fkey (→ users), catalogs.category_id FK
    # (→ categories).  After move these become cross-schema FKs pointing at
    # iam.users / category.categories respectively (after iam/category waves).
    # ------------------------------------------------------------------
    op.execute(sa.text("ALTER TABLE public.catalogs SET SCHEMA catalog"))
    _LOG.info(
        "%s public.catalogs moved to catalog.catalogs "
        "(indexes: idx_catalogs_user, idx_catalogs_user_created, "
        "idx_catalogs_category_id — all preserved).",
        _MIGRATION_TAG,
    )

    # ------------------------------------------------------------------
    # Step 4 — Move products table
    # products.catalog_id → catalog.catalogs.id becomes intra-schema FK
    # (both now in catalog schema) — fully valid, intact.
    # products.user_id → users.id: cross-schema FK (catalog → iam/public)
    # products.category_id → categories.id: cross-schema FK (catalog → category/public)
    # All 5 btree indexes preserved (see migration docstring).
    # ------------------------------------------------------------------
    op.execute(sa.text("ALTER TABLE public.products SET SCHEMA catalog"))
    _LOG.info(
        "%s public.products moved to catalog.products "
        "(indexes: idx_products_user, idx_products_category, idx_products_status, "
        "idx_products_user_status, idx_products_catalog_id — all preserved; "
        "products.catalog_id FK now intra-schema catalog.catalogs.id).",
        _MIGRATION_TAG,
    )

    # ------------------------------------------------------------------
    # Step 5 — Move product_drafts table
    # product_drafts.product_id → catalog.products.id becomes intra-schema
    # (both in catalog schema) — fully valid, intact.
    # product_drafts.user_id → users.id: cross-schema FK (catalog → iam/public)
    # Composite PK (user_id, product_id) is preserved.
    # Indexes preserved: idx_product_drafts_product_id, idx_product_drafts_saved_at
    # ------------------------------------------------------------------
    op.execute(sa.text("ALTER TABLE public.product_drafts SET SCHEMA catalog"))
    _LOG.info(
        "%s public.product_drafts moved to catalog.product_drafts "
        "(composite PK preserved; indexes: idx_product_drafts_product_id, "
        "idx_product_drafts_saved_at — both preserved; "
        "product_drafts.product_id FK now intra-schema catalog.products.id).",
        _MIGRATION_TAG,
    )

    _LOG.info(
        "%s Upgrade complete. 3 tables now in catalog schema: "
        "catalogs, products, product_drafts. "
        "Monolith head f31c75438e61 is UNCHANGED.",
        _MIGRATION_TAG,
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Move 3 tables back from catalog schema to public schema.

    Reverses the upgrade in exactly the reverse order (product_drafts first,
    then products, then catalogs) to respect FK dependency ordering — though
    SET SCHEMA is DDL that Postgres executes atomically, order still matters
    for clarity and for correctness if a future FK enforcement is added.

    No integrity scan needed on downgrade — we are restoring the original
    public layout which was already valid.

    FK constraints: after downgrade, the cross-schema FK objects (user_id,
    category_id) revert to intra-schema references to public.users and
    public.categories, which is the original valid state.
    """
    op.execute(sa.text("ALTER TABLE catalog.product_drafts SET SCHEMA public"))
    _LOG.info(
        "%s catalog.product_drafts moved back to public.product_drafts (downgrade). "
        "Indexes idx_product_drafts_product_id, idx_product_drafts_saved_at preserved.",
        _MIGRATION_TAG,
    )

    op.execute(sa.text("ALTER TABLE catalog.products SET SCHEMA public"))
    _LOG.info(
        "%s catalog.products moved back to public.products (downgrade). "
        "All 5 btree indexes preserved.",
        _MIGRATION_TAG,
    )

    op.execute(sa.text("ALTER TABLE catalog.catalogs SET SCHEMA public"))
    _LOG.info(
        "%s catalog.catalogs moved back to public.catalogs (downgrade). "
        "All 3 btree indexes preserved.",
        _MIGRATION_TAG,
    )

    _LOG.info(
        "%s Downgrade complete. All 3 tables restored to public schema.",
        _MIGRATION_TAG,
    )
