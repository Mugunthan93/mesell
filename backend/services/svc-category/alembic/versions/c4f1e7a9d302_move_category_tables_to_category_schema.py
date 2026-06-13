"""Move 4 global category tables from public schema to category schema.

This is the first (and root) migration in the svc-category standalone Alembic
chain.  It is ENTIRELY SEPARATE from the monolith chain (head f31c75438e61).

Context
-------
MASTER_PLAN §2.D assigns the 4 GLOBAL category tables to Postgres schema
``category`` as part of the V1.5 schema-per-service isolation strategy.
SUB_PLAN_0F_category_extraction.md §DB-tables-owned confirms the 4 tables.

Verified from AS-BUILT source (file:line, SOURCE WINS per recipe §0):
  - ``categories``       — backend/app/shared/models/category.py:39 __tablename__
  - ``templates``        — backend/app/shared/models/template.py __tablename__
  - ``field_enum_values`` — backend/app/shared/models/field_enum_value.py __tablename__
  - ``field_aliases``    — backend/app/shared/models/field_alias.py __tablename__
  ORM imports cited at repository.py:42-44 (Category, FieldEnumValue, Template).
  field_aliases is not imported as ORM in repository.py (repository.py:14 docstring)
  but moves for locality per sub-plan §DB-tables-owned rationale.

GIN Index preservation (CRITICAL — R5)
---------------------------------------
Migration a1b2c3d4e5f6 created 3 pg_trgm GIN indexes on ``categories`` via
CREATE INDEX CONCURRENTLY (database-builder MEMORY Session 2 G4+G1):
  idx_categories_path_trgm        — GIN on path (gin_trgm_ops)
  idx_categories_leaf_name_trgm   — GIN on leaf_name (gin_trgm_ops)
  idx_categories_super_name_trgm  — GIN on super_name (gin_trgm_ops)
PostgreSQL ALTER TABLE ... SET SCHEMA preserves ALL indexes (btree + GIN) intact.
The index names, index types, and operator classes are unchanged by the schema move.
Post-upgrade, the indexes exist as category.idx_categories_* and are still valid.

Risk #5 integrity pre-scan
---------------------------
Before the schema move we verify referential integrity for FK-bearing tables.
``categories.template_id`` references ``public.templates.id`` — both tables move
together, so this FK resolves within the same operation; no cross-schema break.
``field_enum_values.category_id`` references ``public.categories.id`` — both move.
``catalogs.category_id`` FK references ``public.categories(id)`` and is a cross-schema
FK that will be severed post-extraction (catalog-svc will switch to HTTP shim).
At schema-move time the cross-schema FK (catalogs→categories) is NOT yet severed
(catalog is still in-process), so the move is safe.

The REAL orphan risk is ``field_enum_values.category_id`` rows pointing at missing
category rows.  We pre-scan for this before the move.

Cross-schema FK note (categories ← catalogs / products)
----------------------------------------------------------
``catalogs.category_id`` and ``products.category_id`` (in public schema) reference
``public.categories.id``.  After the schema move these become cross-schema FKs
(public.catalogs → category.categories).  PostgreSQL SUPPORTS cross-schema FKs.
The FK constraint itself remains valid because both schemas are in the same DB.
When catalog-svc eventually extracts (MS-H), it will switch to the HTTP shim and
drop the cross-schema FK.  Until then, the cross-schema FK is a deliberate state
per MASTER_PLAN §2.D.

Upgrade
-------
1. Risk#5 scan: COUNT of field_enum_values.category_id with no match in categories.
   Raise if orphans found.
2. Ensure the ``category`` schema exists (idempotent; infra runbook also creates it).
3. ALTER TABLE public.categories SET SCHEMA category.
4. ALTER TABLE public.templates SET SCHEMA category.
5. ALTER TABLE public.field_enum_values SET SCHEMA category.
6. ALTER TABLE public.field_aliases SET SCHEMA category.

Downgrade
---------
Reverse: move all 4 tables back to public schema.

Post-upgrade state
------------------
- ``category.categories``, ``category.templates``, ``category.field_enum_values``,
  ``category.field_aliases`` exist (tables in schema ``category``).
- The original ``public.*`` names for those 4 tables do NOT exist.
- ``category.alembic_version`` row tracks this migration (version_table_schema=
  "category" in env.py).
- The monolith's ``public.alembic_version`` row is UNCHANGED (head f31c75438e61).
- GIN indexes idx_categories_*_trgm survive intact (PostgreSQL preserves all
  indexes on ALTER TABLE ... SET SCHEMA).
- Cross-schema FKs from public.catalogs + public.products to category.categories
  remain valid (PostgreSQL supports cross-schema FKs in same DB).

Revision ID: c4f1e7a9d302
Revises: (none — root of svc-category chain)
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

revision: str = "c4f1e7a9d302"
down_revision: Union[str, None] = None  # root of the svc-category chain
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOG = logging.getLogger("alembic.runtime.migration")

_MIGRATION_TAG = "[svc-category migration c4f1e7a9d302]"

# Risk#5 orphan scan: field_enum_values rows whose category_id has no match
# in categories.  Both tables are being moved together, but orphans would
# indicate pre-existing data corruption that must be resolved first.
_ORPHAN_SCAN_SQL = sa.text(
    """
    SELECT COUNT(*) AS orphan_count
    FROM public.field_enum_values fev
    WHERE NOT EXISTS (
        SELECT 1
        FROM public.categories c
        WHERE c.id = fev.category_id
    )
    """
)

_ORPHAN_DETAIL_SQL = sa.text(
    """
    SELECT fev.id, fev.category_id, fev.field_name
    FROM public.field_enum_values fev
    WHERE NOT EXISTS (
        SELECT 1
        FROM public.categories c
        WHERE c.id = fev.category_id
    )
    LIMIT 20
    """
)


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Move 4 global category tables from public schema to category schema.

    Step 1: Risk#5 integrity pre-scan — field_enum_values orphan check.
    Step 2: Ensure category schema exists (idempotent).
    Step 3: ALTER TABLE public.categories SET SCHEMA category.
    Step 4: ALTER TABLE public.templates SET SCHEMA category.
    Step 5: ALTER TABLE public.field_enum_values SET SCHEMA category.
    Step 6: ALTER TABLE public.field_aliases SET SCHEMA category.

    GIN index preservation: PostgreSQL ALTER TABLE ... SET SCHEMA preserves all
    indexes (including GIN pg_trgm indexes from migration a1b2c3d4e5f6).
    The browse ILIKE/similarity queries continue to use Bitmap Index Scan after
    the schema move.
    """
    # ------------------------------------------------------------------
    # Step 1 — Risk#5 integrity pre-scan (online mode only)
    # ------------------------------------------------------------------
    if context.is_offline_mode():
        _LOG.info(
            "%s OFFLINE MODE — Risk#5 scan SQL must be run manually before "
            "applying this migration:\n"
            "SELECT COUNT(*) AS orphan_count FROM public.field_enum_values fev "
            "WHERE NOT EXISTS (SELECT 1 FROM public.categories c WHERE c.id = fev.category_id);",
            _MIGRATION_TAG,
        )
    else:
        conn = op.get_bind()
        _LOG.info(
            "%s Risk#5 pre-scan: checking field_enum_values.category_id referential integrity ...",
            _MIGRATION_TAG,
        )

        row = conn.execute(_ORPHAN_SCAN_SQL).fetchone()
        orphan_count: int = row[0] if row is not None else 0

        _LOG.info(
            "%s Risk#5 pre-scan result: %d orphaned field_enum_values.category_id row(s) found.",
            _MIGRATION_TAG,
            orphan_count,
        )

        if orphan_count > 0:
            detail_rows = conn.execute(_ORPHAN_DETAIL_SQL).fetchall()
            for detail in detail_rows:
                _LOG.error(
                    "%s Orphan row — field_enum_values.id=%s category_id=%s field_name=%s "
                    "(no matching categories row)",
                    _MIGRATION_TAG,
                    detail[0],
                    detail[1],
                    detail[2],
                )
            raise RuntimeError(
                f"{_MIGRATION_TAG} ABORT: Risk#5 integrity pre-scan found "
                f"{orphan_count} orphaned field_enum_values.category_id row(s) with no "
                f"matching public.categories row. Resolve the data integrity issue before "
                f"re-running this migration. Up to 20 offending rows have been emitted to "
                f"the migration log above."
            )

        _LOG.info("%s Risk#5 pre-scan PASSED — zero orphans.", _MIGRATION_TAG)

    # ------------------------------------------------------------------
    # Step 2 — Ensure category schema exists (idempotent guard)
    # The env.py do_run_migrations() also issues this before configure().
    # Belt-and-suspenders: emit it here too so the schema exists when the
    # ALTER TABLE statements run inside the migration transaction.
    # ------------------------------------------------------------------
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS category"))
    _LOG.info("%s Schema 'category' ensured.", _MIGRATION_TAG)

    # ------------------------------------------------------------------
    # Step 3 — Move categories table
    # GIN indexes (idx_categories_path_trgm, idx_categories_leaf_name_trgm,
    # idx_categories_super_name_trgm) are preserved by PostgreSQL automatically.
    # B-tree indexes (idx_categories_super, idx_categories_template,
    # idx_categories_meesho_leaf) are also preserved.
    # Cross-schema FKs from public.catalogs.category_id and
    # public.products.category_id will reference category.categories after
    # this move — PostgreSQL supports cross-schema FKs within the same database.
    # ------------------------------------------------------------------
    op.execute(sa.text("ALTER TABLE public.categories SET SCHEMA category"))
    _LOG.info(
        "%s public.categories moved to category.categories (all GIN + btree indexes preserved).",
        _MIGRATION_TAG,
    )

    # ------------------------------------------------------------------
    # Step 4 — Move templates table
    # The FK categories.template_id → templates.id resolves to
    # category.categories.template_id → category.templates.id after both moves.
    # The FK constraint itself is preserved by PostgreSQL during SET SCHEMA.
    # ------------------------------------------------------------------
    op.execute(sa.text("ALTER TABLE public.templates SET SCHEMA category"))
    _LOG.info("%s public.templates moved to category.templates.", _MIGRATION_TAG)

    # ------------------------------------------------------------------
    # Step 5 — Move field_enum_values table
    # FK field_enum_values.category_id → categories.id becomes an
    # intra-schema FK (both now in category schema) — valid and intact.
    # ------------------------------------------------------------------
    op.execute(sa.text("ALTER TABLE public.field_enum_values SET SCHEMA category"))
    _LOG.info(
        "%s public.field_enum_values moved to category.field_enum_values.",
        _MIGRATION_TAG,
    )

    # ------------------------------------------------------------------
    # Step 6 — Move field_aliases table
    # field_aliases is seed-time only (not imported as ORM in repository.py).
    # It moves for locality (all 4 category-owned tables in one schema).
    # No FK cross-references from other tables to field_aliases.
    # ------------------------------------------------------------------
    op.execute(sa.text("ALTER TABLE public.field_aliases SET SCHEMA category"))
    _LOG.info(
        "%s public.field_aliases moved to category.field_aliases.",
        _MIGRATION_TAG,
    )

    _LOG.info(
        "%s Upgrade complete. 4 tables now in category schema: "
        "categories, templates, field_enum_values, field_aliases.",
        _MIGRATION_TAG,
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Move 4 tables back from category schema to public schema.

    Reverses the upgrade in exactly the reverse order (field_aliases first,
    then field_enum_values, then templates, then categories) to respect FK
    dependency ordering (though SET SCHEMA is DDL that Postgres executes
    atomically, order still matters for clarity and safety).

    No integrity scan needed on downgrade — we are restoring the original
    public layout which was already valid.
    """
    op.execute(sa.text("ALTER TABLE category.field_aliases SET SCHEMA public"))
    _LOG.info(
        "%s category.field_aliases moved back to public.field_aliases (downgrade).",
        _MIGRATION_TAG,
    )

    op.execute(sa.text("ALTER TABLE category.field_enum_values SET SCHEMA public"))
    _LOG.info(
        "%s category.field_enum_values moved back to public.field_enum_values (downgrade).",
        _MIGRATION_TAG,
    )

    op.execute(sa.text("ALTER TABLE category.templates SET SCHEMA public"))
    _LOG.info(
        "%s category.templates moved back to public.templates (downgrade).",
        _MIGRATION_TAG,
    )

    op.execute(sa.text("ALTER TABLE category.categories SET SCHEMA public"))
    _LOG.info(
        "%s category.categories moved back to public.categories (downgrade). "
        "GIN + btree indexes are preserved by PostgreSQL.",
        _MIGRATION_TAG,
    )

    _LOG.info(
        "%s Downgrade complete. All 4 tables restored to public schema.",
        _MIGRATION_TAG,
    )
