"""Move product_images table from public schema to image schema (Option B — no products read grant).

This is the first (and currently only) migration in the svc-image standalone
Alembic chain.  It is SEPARATE from the monolith chain (head f31c75438e61).

Context
-------
MASTER_PLAN §2.D assigns the ``product_images`` table to Postgres schema
``image`` as part of the V1.5 schema-per-service isolation strategy.  This
migration effects that move.  The monolith's ``public.product_images`` is
moved; the monolith's Alembic chain is NOT touched.

The migration is authored per spec §1 Phase-A1 (database-builder dispatch)
from backend-coordinator spec_msC_backend_EXECUTION.md, authoritative at
origin/feature/microservices-image/integration 3dc0f91.

Option B — cross-schema tenancy (RULED by founder 2026-06-13)
-------------------------------------------------------------
SUB_PLAN_0C_image_extraction.md §0.10 + spec_msC_backend_EXECUTION.md §0.3
rule OPTION B: svc-image resolves ownership via the catalog
``assert_product_ownership`` HTTP shim, NOT a cross-schema DB read-grant.

Concrete consequence in this migration:
  - The existing FK constraint ``product_images_product_id_fkey`` (references
    ``public.products.id``, ON DELETE CASCADE, auto-named by PostgreSQL from
    the Alembic baseline migration 935e55b4852c that did not provide an explicit
    name) is DROPPED BEFORE the schema move.  Moving the table to schema
    ``image`` while the FK still references ``public.products`` would create a
    cross-schema FK — that is exactly what Option B disallows.
  - After dropping the FK, the ``product_id`` column remains as a plain
    indexed column (``idx_product_images_product_id`` is preserved — it is
    already in the public schema and follows the table into ``image``).
  - Ownership is enforced at RUNTIME by the svc-image repository layer:
    every write path calls ``assert_product_ownership`` BEFORE any SQL, so
    the presence of a matching ``products`` row is verified via HTTP shim,
    not via a DB FK.
  - ``image_user`` is granted NO ``SELECT`` access on ``public.products``.
    The ONLY cross-schema grant required by svc-image is:
      ``GRANT INSERT ON public.audit_events TO image_user``
    (worker direct-write audit per §15.E exception + SUB_PLAN_0C §3.F).
    That grant is infrastructure-side (infra-builder's K8s/Postgres runbook);
    it is documented here for traceability but NOT executed in this migration.

Risk #5 integrity pre-scan (spec §1 Phase-A1)
----------------------------------------------
Before the schema move (and before dropping the FK) we verify that every
``product_images.product_id`` resolves to a real row in ``public.products``.
This is a one-shot data-quality gate executed at migration time when the
``products`` table is still in ``public`` (catalog is extracted last, at MS-5).

If orphaned rows are found the migration logs them and raises, aborting the
transaction cleanly.  Do NOT proceed with the schema move if orphans exist —
they indicate a data integrity problem that must be resolved manually.

FK drop justification (OPTION B — per spec, not oversight)
----------------------------------------------------------
Dropping the FK is INTENTIONAL and FOUNDER-RULED (Option B, 2026-06-13):
  - A cross-schema FK from ``image.product_images`` to ``public.products``
    would tightly couple the two schemas and prevent independent schema
    migration — contradicting MASTER_PLAN §2.D.
  - Runtime ownership is enforced by the ``assert_product_ownership`` HTTP
    shim (service.py:162 / :248); the FK was defensive-only and is replaced
    by the application-layer gate under Option B.
  - ON DELETE CASCADE behaviour is preserved via the application layer:
    the catalog service calls the image-service API to delete images when a
    product is soft-deleted (the cascade is product-lifecycle logic, owned
    by the catalog module's domain, not a DB-level cascade across schemas).

Upgrade
-------
1. Risk#5 scan: verify every product_images.product_id has a matching
   products row.  Raise if orphans found.
2. DROP the FK constraint (product_images_product_id_fkey) — Option B.
3. Ensure the ``image`` schema exists (idempotent guard).
4. ALTER TABLE public.product_images SET SCHEMA image.

Downgrade
---------
1. ALTER TABLE image.product_images SET SCHEMA public.
2. Re-add the FK constraint (product_images_product_id_fkey) referencing
   public.products.id ON DELETE CASCADE.
   Note: downgrade is only safe if public.products exists (monolith not
   yet extracted to catalog schema at MS-5 — catalog is always last).

Post-upgrade state
------------------
- ``image.product_images`` exists (table in schema ``image``).
- ``public.product_images`` does NOT exist.
- ``image.alembic_version`` row tracks this migration (version_table_schema=
  "image" in env.py).
- The monolith's ``public.alembic_version`` row is UNCHANGED (head
  f31c75438e61).
- The FK from product_images → products is DROPPED (Option B).
- ``product_id`` column is a plain indexed column (``idx_product_images_product_id``
  follows the table into ``image`` schema automatically).
- image_user holds NO SELECT grant on public.products.
- GRANT INSERT ON public.audit_events TO image_user: infra-builder's runbook.

Revision ID: c2a4e8f1d7b3
Revises: (none — root of svc-image chain)
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

revision: str = "c2a4e8f1d7b3"
down_revision: Union[str, None] = None  # root of the svc-image chain
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOG = logging.getLogger("alembic.runtime.migration")

# The FK name auto-generated by PostgreSQL from the baseline migration
# 935e55b4852c which used:
#   sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE')
# (no explicit name= argument).  PostgreSQL convention: {table}_{col}_fkey.
_FK_NAME = "product_images_product_id_fkey"

# Risk#5 scan: every product_images.product_id must have a real products row.
# This is executed in the monolith DB where products is still in public schema
# (catalog extracts LAST at MS-5, so public.products is guaranteed to exist
# at MS-C time).
_SCAN_SQL = sa.text(
    """
    SELECT COUNT(*) AS orphan_count
    FROM public.product_images pi
    WHERE NOT EXISTS (
        SELECT 1
        FROM public.products p
        WHERE p.id = pi.product_id
    )
    """
)

_ORPHAN_DETAIL_SQL = sa.text(
    """
    SELECT pi.id, pi.product_id
    FROM public.product_images pi
    WHERE NOT EXISTS (
        SELECT 1
        FROM public.products p
        WHERE p.id = pi.product_id
    )
    LIMIT 20
    """
)

# Total row count scan — logged for audit trail.
_ROW_COUNT_SQL = sa.text("SELECT COUNT(*) AS total FROM public.product_images")

# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Move public.product_images → image.product_images (Option B).

    Step 1: Risk#5 integrity pre-scan.
    Step 2: Drop the FK constraint (Option B — no cross-schema FK).
    Step 3: Ensure image schema exists.
    Step 4: ALTER TABLE product_images SET SCHEMA image.
    """
    # ------------------------------------------------------------------
    # Step 1 — Risk#5 integrity pre-scan (spec §1 Phase-A1)
    # In offline (--sql) mode there is no live DB connection; skip the
    # live query and log the scan SQL as a manual instruction.
    # ------------------------------------------------------------------
    if context.is_offline_mode():
        _LOG.info(
            "[svc-image migration c2a4e8f1d7b3] OFFLINE MODE — "
            "Risk#5 scan SQL must be run manually before applying this migration:\n"
            "SELECT COUNT(*) AS orphan_count FROM public.product_images pi "
            "WHERE NOT EXISTS (SELECT 1 FROM public.products p WHERE p.id = pi.product_id);"
        )
    else:
        conn = op.get_bind()

        # Total row count for audit trail.
        row_count_row = conn.execute(_ROW_COUNT_SQL).fetchone()
        total_rows: int = row_count_row[0] if row_count_row is not None else 0
        _LOG.info(
            "[svc-image migration c2a4e8f1d7b3] Risk#5 pre-scan: "
            "product_images contains %d row(s) total. "
            "Checking product_id referential integrity ...",
            total_rows,
        )

        row = conn.execute(_SCAN_SQL).fetchone()
        orphan_count: int = row[0] if row is not None else 0

        _LOG.info(
            "[svc-image migration c2a4e8f1d7b3] Risk#5 pre-scan result: "
            "%d orphaned product_images.product_id row(s) found (no matching products row).",
            orphan_count,
        )

        if orphan_count > 0:
            # Emit detail rows (up to 20) into the migration log for forensics.
            detail_rows = conn.execute(_ORPHAN_DETAIL_SQL).fetchall()
            for detail in detail_rows:
                _LOG.error(
                    "[svc-image migration c2a4e8f1d7b3] Orphan row — "
                    "image.id=%s product_id=%s (no matching public.products row)",
                    detail[0],
                    detail[1],
                )
            raise RuntimeError(
                f"[svc-image migration c2a4e8f1d7b3] ABORT: Risk#5 integrity pre-scan found "
                f"{orphan_count} orphaned product_images.product_id row(s) with no matching "
                f"public.products row. Resolve the data integrity issue before re-running "
                f"this migration. Up to 20 offending rows have been emitted to the "
                f"migration log above."
            )

        _LOG.info("[svc-image migration c2a4e8f1d7b3] Risk#5 pre-scan PASSED — zero orphans.")

    # ------------------------------------------------------------------
    # Step 2 — Drop the FK constraint (Option B ruling)
    # The FK product_images_product_id_fkey references public.products.id.
    # Under Option B (founder-RULED 2026-06-13), svc-image must NOT have a
    # cross-schema FK to public.products.  Dropping it makes product_id a
    # plain indexed column; ownership is enforced via the catalog HTTP shim.
    #
    # The drop must happen BEFORE SET SCHEMA because Postgres cannot move a
    # table that has an FK referencing a table in a different schema if that
    # would create an invalid cross-schema reference in the new schema context.
    # Dropping the FK first, then moving, is the safe sequence.
    # ------------------------------------------------------------------
    op.drop_constraint(_FK_NAME, "product_images", type_="foreignkey")
    _LOG.info(
        "[svc-image migration c2a4e8f1d7b3] Dropped FK constraint '%s' "
        "(Option B — ownership via HTTP shim, not cross-schema SQL).",
        _FK_NAME,
    )

    # ------------------------------------------------------------------
    # Step 3 — Ensure image schema exists
    # (Idempotent guard; infra runbook also creates it with role grant)
    # NOTE: env.py's do_run_migrations() already runs CREATE SCHEMA IF NOT
    # EXISTS image BEFORE this upgrade() is called, so the schema is
    # guaranteed to exist at this point.  This step is a belt-and-suspenders
    # guard for any execution path that bypasses env.py (e.g. direct op.execute
    # in tests).
    # ------------------------------------------------------------------
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS image"))
    _LOG.info("[svc-image migration c2a4e8f1d7b3] Schema 'image' ensured.")

    # ------------------------------------------------------------------
    # Step 4 — Move table to image schema
    # After this statement public.product_images ceases to exist.
    # The index idx_product_images_product_id follows the table automatically
    # (PostgreSQL moves all table-owned indexes when the table is moved).
    # The UniqueConstraint (uq_product_images_product_order) and CheckConstraint
    # (ck_product_images_order_idx) also follow the table automatically.
    # ------------------------------------------------------------------
    op.execute(sa.text("ALTER TABLE public.product_images SET SCHEMA image"))
    _LOG.info(
        "[svc-image migration c2a4e8f1d7b3] public.product_images moved to image.product_images."
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Move image.product_images back to public schema and restore FK.

    This is the tested downgrade (SET SCHEMA public + re-add FK).

    Pre-conditions for safe downgrade:
    - public.products must exist (catalog has NOT been extracted to its own
      schema at MS-5 yet — catalog always extracts last; downgrade before
      MS-5 is safe).
    - No cross-schema dependencies have been introduced on image.product_images
      since the upgrade was applied.
    """
    # Step 1: Move table back to public schema.
    op.execute(sa.text("ALTER TABLE image.product_images SET SCHEMA public"))
    _LOG.info(
        "[svc-image migration c2a4e8f1d7b3] "
        "image.product_images moved back to public.product_images (downgrade)."
    )

    # Step 2: Re-add the FK constraint referencing public.products.id.
    # This restores the original monolith state (ON DELETE CASCADE, auto-named).
    op.create_foreign_key(
        _FK_NAME,
        "product_images",
        "products",
        ["product_id"],
        ["id"],
        ondelete="CASCADE",
    )
    _LOG.info(
        "[svc-image migration c2a4e8f1d7b3] "
        "FK constraint '%s' (product_images.product_id → public.products.id) "
        "restored (downgrade).",
        _FK_NAME,
    )
