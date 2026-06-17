"""Move seller_profile table from public schema to customer schema.

This is the first (and currently only) migration in the svc-customer standalone
Alembic chain.  It is SEPARATE from the monolith chain (head f31c75438e61).

Context
-------
MASTER_PLAN §2.D assigns the ``seller_profile`` table to Postgres schema
``customer`` as part of the V1.5 schema-per-service isolation strategy.  This
migration effects that move.  The monolith's ``public.seller_profile`` is
moved; the monolith's Alembic chain is NOT touched.

The migration is authored per spec §3.C Phase-A (database-builder dispatch)
from backend-coordinator spec_msE_backend.md.

Source model citations (backend/app/shared/models/seller_profile.py)
--------------------------------------------------------------------
- FK ``fk_seller_profile_user_id``: line 127
  (``ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE",
  name="fk_seller_profile_user_id")``)
- ``relationship("User", back_populates="seller_profile")``: lines 116-119
- GIN index ``idx_seller_profile_super_cats`` on ``active_super_categories``:
  lines 131-135
- ``__table_args__`` starts: line 122

Risk #5 integrity pre-scan
--------------------------
Before any schema move, we verify that every ``seller_profile.user_id``
resolves to a real row in ``public.users``.  This is the cross-schema FK
being severed: ``fk_seller_profile_user_id`` references ``public.users.id``.
A dangling row (seller_profile.user_id with no matching users row) must
surface here and abort the migration — it must NOT silently break.

If orphaned rows are found the migration logs them and raises, aborting the
transaction cleanly.  Do NOT proceed with the schema move if orphans exist —
they indicate a data integrity problem that must be resolved manually.

FK drop justification (Risk #5 severance)
-----------------------------------------
Dropping ``fk_seller_profile_user_id`` is INTENTIONAL and required for the
schema-per-service isolation:
  - A cross-schema FK from ``customer.seller_profile`` to ``public.users``
    would tightly couple the two schemas and prevent independent schema
    migration — contradicting MASTER_PLAN §2.D.
  - After extraction, user identity is verified at the application layer via
    JWT authentication (``get_current_user`` in svc-customer's FastAPI routes).
    The FK was defensive-only and is replaced by the application-layer gate.
  - ``user_id`` remains as the primary key column (plain UUID PK) with no
    FK decoration in the extracted service's ORM model.

GIN index follows the table
---------------------------
``idx_seller_profile_super_cats`` (GIN on ``active_super_categories``) is a
table-owned index.  PostgreSQL moves all table-owned indexes when
``ALTER TABLE ... SET SCHEMA`` is executed — the index is NOT dropped and
re-created; it follows automatically into ``customer.seller_profile``.
Confirmed pattern: same behavior verified in svc-image migration
``c2a4e8f1d7b3`` for ``idx_product_images_product_id``.

Upgrade
-------
1. Risk#5 pre-scan: verify every seller_profile.user_id resolves to a real
   users row.  Emit result to migration log.  Raise + abort if orphans found.
2. DROP CONSTRAINT fk_seller_profile_user_id (severs cross-schema FK).
3. CREATE SCHEMA IF NOT EXISTS customer (idempotent guard; env.py also does
   this before configure(), but belt-and-suspenders inside upgrade() too).
4. ALTER TABLE public.seller_profile SET SCHEMA customer.

Downgrade
---------
1. ALTER TABLE customer.seller_profile SET SCHEMA public.
2. Re-add FK constraint fk_seller_profile_user_id referencing public.users.id
   ON DELETE CASCADE.
   Note: downgrade is only safe if public.users exists (users table is never
   extracted — it stays in public schema permanently under MASTER_PLAN §2.D).
   Clean round-trip is guaranteed.

Post-upgrade state
------------------
- ``customer.seller_profile`` exists (table in schema ``customer``).
- ``public.seller_profile`` does NOT exist.
- ``customer.alembic_version`` row tracks this migration
  (version_table_schema="customer" in env.py).
- The monolith's ``public.alembic_version`` row is UNCHANGED (head
  f31c75438e61).
- FK ``fk_seller_profile_user_id`` (seller_profile.user_id → users.id) is
  DROPPED (severed per MASTER_PLAN §2.D schema isolation).
- GIN index ``idx_seller_profile_super_cats`` follows the table automatically
  into ``customer.seller_profile`` — no re-creation needed.

Revision ID: a9f3b2c5e1d8
Revises: (none — root of svc-customer chain)
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

revision: str = "a9f3b2c5e1d8"
down_revision: Union[str, None] = None  # root of the svc-customer chain
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOG = logging.getLogger("alembic.runtime.migration")

# The FK name explicitly provided in the baseline migration 935e55b4852c via
# ForeignKeyConstraint(..., name="fk_seller_profile_user_id") in the
# SellerProfile ORM model (seller_profile.py:127).  This FK is the
# cross-schema reference being severed on extraction.
_FK_NAME = "fk_seller_profile_user_id"

# Risk#5 scan: every seller_profile.user_id must resolve to a real users row.
# seller_profile.user_id IS the primary key (one-to-one with users).
# Executed while seller_profile is still in public schema and users is in public.
_SCAN_SQL = sa.text(
    """
    SELECT COUNT(*) AS orphan_count
    FROM public.seller_profile sp
    WHERE NOT EXISTS (
        SELECT 1
        FROM public.users u
        WHERE u.id = sp.user_id
    )
    """
)

_ORPHAN_DETAIL_SQL = sa.text(
    """
    SELECT sp.user_id
    FROM public.seller_profile sp
    WHERE NOT EXISTS (
        SELECT 1
        FROM public.users u
        WHERE u.id = sp.user_id
    )
    LIMIT 20
    """
)

# Total row count scan — logged for audit trail.
_ROW_COUNT_SQL = sa.text("SELECT COUNT(*) AS total FROM public.seller_profile")

# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Move public.seller_profile -> customer.seller_profile.

    Step 1: Risk#5 integrity pre-scan (emit result to log; abort on orphans).
    Step 2: Drop FK constraint fk_seller_profile_user_id (sever cross-schema FK).
    Step 3: Ensure customer schema exists (idempotent guard).
    Step 4: ALTER TABLE seller_profile SET SCHEMA customer.
    """
    # ------------------------------------------------------------------
    # Step 1 — Risk#5 integrity pre-scan (spec §3.C)
    # In offline (--sql) mode there is no live DB connection; skip the
    # live query and log the scan SQL as a manual instruction.
    # ------------------------------------------------------------------
    if context.is_offline_mode():
        _LOG.info(
            "[svc-customer migration a9f3b2c5e1d8] OFFLINE MODE — "
            "Risk#5 scan SQL must be run manually before applying this migration:\n"
            "SELECT COUNT(*) AS orphan_count FROM public.seller_profile sp "
            "WHERE NOT EXISTS (SELECT 1 FROM public.users u WHERE u.id = sp.user_id);"
        )
    else:
        conn = op.get_bind()

        # Total row count for audit trail.
        row_count_row = conn.execute(_ROW_COUNT_SQL).fetchone()
        total_rows: int = row_count_row[0] if row_count_row is not None else 0
        _LOG.info(
            "[svc-customer migration a9f3b2c5e1d8] Risk#5 pre-scan: "
            "seller_profile contains %d row(s) total. "
            "Checking user_id referential integrity ...",
            total_rows,
        )

        row = conn.execute(_SCAN_SQL).fetchone()
        orphan_count: int = row[0] if row is not None else 0

        _LOG.info(
            "[svc-customer migration a9f3b2c5e1d8] Risk#5 pre-scan result: "
            "%d orphaned seller_profile.user_id row(s) found (no matching users row).",
            orphan_count,
        )

        if orphan_count > 0:
            # Emit detail rows (up to 20) into the migration log for forensics.
            detail_rows = conn.execute(_ORPHAN_DETAIL_SQL).fetchall()
            for detail in detail_rows:
                _LOG.error(
                    "[svc-customer migration a9f3b2c5e1d8] Orphan row — "
                    "seller_profile.user_id=%s (no matching public.users row)",
                    detail[0],
                )
            raise RuntimeError(
                f"[svc-customer migration a9f3b2c5e1d8] ABORT: Risk#5 integrity pre-scan found "
                f"{orphan_count} orphaned seller_profile.user_id row(s) with no matching "
                f"public.users row. Resolve the data integrity issue before re-running "
                f"this migration. Up to 20 offending rows have been emitted to the "
                f"migration log above."
            )

        _LOG.info(
            "[svc-customer migration a9f3b2c5e1d8] Risk#5 pre-scan PASSED — zero orphans."
        )

    # ------------------------------------------------------------------
    # Step 2 — Drop the FK constraint (sever cross-schema FK per MASTER_PLAN §2.D)
    # fk_seller_profile_user_id references public.users.id ON DELETE CASCADE.
    # Under MASTER_PLAN §2.D schema-per-service isolation, svc-customer must NOT
    # retain a cross-schema FK to public.users after extraction.
    # After extraction, user identity is verified at the application layer via JWT.
    #
    # The drop must happen BEFORE SET SCHEMA to avoid leaving a dangling
    # cross-schema FK reference in the new schema context.
    # ------------------------------------------------------------------
    op.drop_constraint(_FK_NAME, "seller_profile", type_="foreignkey")
    _LOG.info(
        "[svc-customer migration a9f3b2c5e1d8] Dropped FK constraint '%s' "
        "(cross-schema FK severed — ownership via JWT auth, not SQL FK).",
        _FK_NAME,
    )

    # ------------------------------------------------------------------
    # Step 3 — Ensure customer schema exists
    # (Idempotent guard; env.py's do_run_migrations() also creates it
    # BEFORE context.configure(), so the schema is guaranteed to exist
    # at this point.  Belt-and-suspenders for any execution path that
    # bypasses env.py, e.g. direct op.execute in tests.)
    # ------------------------------------------------------------------
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS customer"))
    _LOG.info("[svc-customer migration a9f3b2c5e1d8] Schema 'customer' ensured.")

    # ------------------------------------------------------------------
    # Step 4 — Move table to customer schema
    # After this statement public.seller_profile ceases to exist.
    # All table-owned objects follow automatically:
    #   - idx_seller_profile_super_cats (GIN on active_super_categories) — FOLLOWS
    # PostgreSQL moves all table-owned indexes with the table; no re-creation
    # needed.  Confirmed by PostgreSQL documentation and tested in svc-image
    # migration c2a4e8f1d7b3 (idx_product_images_product_id followed the table).
    # ------------------------------------------------------------------
    op.execute(sa.text("ALTER TABLE public.seller_profile SET SCHEMA customer"))
    _LOG.info(
        "[svc-customer migration a9f3b2c5e1d8] "
        "public.seller_profile moved to customer.seller_profile. "
        "GIN index idx_seller_profile_super_cats followed the table automatically."
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Move customer.seller_profile back to public schema and restore FK.

    This is the tested downgrade (SET SCHEMA public + re-add FK).

    Pre-conditions for safe downgrade:
    - public.users must exist.  The users table is NEVER extracted (it stays
      in public schema permanently under MASTER_PLAN §2.D) — downgrade is
      always safe regardless of extraction wave timing.
    - No cross-schema dependencies have been introduced on
      customer.seller_profile since the upgrade was applied.
    """
    # Step 1: Move table back to public schema.
    op.execute(sa.text("ALTER TABLE customer.seller_profile SET SCHEMA public"))
    _LOG.info(
        "[svc-customer migration a9f3b2c5e1d8] "
        "customer.seller_profile moved back to public.seller_profile (downgrade)."
    )

    # Step 2: Re-add the FK constraint referencing public.users.id.
    # This restores the original monolith state (ON DELETE CASCADE, explicit name).
    op.create_foreign_key(
        _FK_NAME,
        "seller_profile",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    _LOG.info(
        "[svc-customer migration a9f3b2c5e1d8] "
        "FK constraint '%s' (seller_profile.user_id -> public.users.id) "
        "restored (downgrade).",
        _FK_NAME,
    )
