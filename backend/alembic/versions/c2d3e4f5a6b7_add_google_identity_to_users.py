"""Add Google identity to users (dual-identity: phone OR Google).

google-auth feature (2026-06-18) — MONOLITH chain.

Mirror of the svc-iam migration ``c2d3e4f5a6b7`` (same revision id; the two
Alembic chains are independent — svc-iam tracks its head in
``iam.alembic_version``, the monolith in ``public.alembic_version``).  The
ONLY difference vs the svc-iam copy is the target schema: the monolith
``users`` table is in ``public`` (it has NOT been moved to ``iam`` in the
monolith chain), so this migration operates on ``public.users``.

down_revision = b7c2e1a9d3f4 — the LIVE monolith head re-confirmed at
implementation time (2026-06-18).  The GOOGLE_AUTH_DESIGN_BACKEND.md §B.5
guessed ``f31c75438e61`` but explicitly required re-confirmation; the live
head is ``b7c2e1a9d3f4`` (pricing_calcs forward-estimator columns), which
revises ``f31c75438e61``.  Using the live head avoids head divergence.

See the svc-iam copy's module docstring for the full schema/upgrade/downgrade
rationale and the V1.5 evolution path — it is identical except for the schema.

Revision ID: c2d3e4f5a6b7
Revises: b7c2e1a9d3f4
Create Date: 2026-06-18 00:00:00.000000
"""

from __future__ import annotations

import hashlib
import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b7c2e1a9d3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOG = logging.getLogger("alembic.runtime.migration")

# Monolith: users live in the default 'public' schema (NOT moved to iam here).
_QUALIFIED = "public.users"


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Widen public.users for dual-identity (phone OR Google)."""
    if context.is_offline_mode():
        _LOG.info(
            "[monolith c2d3e4f5a6b7] OFFLINE MODE — the duplicate-email pre-scan "
            "MUST be run manually before applying.  Emitting raw DDL."
        )
        _emit_upgrade_ddl()
        return

    conn = op.get_bind()

    # ── Step 1 — duplicate-email pre-scan (Risk-style abort guard) ──────────
    _LOG.info(
        "[monolith c2d3e4f5a6b7] pre-scan: checking for duplicate non-NULL emails "
        "before adding the UNIQUE(email) index..."
    )
    dup_rows = conn.execute(
        sa.text(
            f"SELECT email, COUNT(*) AS n FROM {_QUALIFIED} "
            f"WHERE email IS NOT NULL GROUP BY email HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if dup_rows:
        for email, n in dup_rows[:20]:
            digest = hashlib.sha256(str(email).encode("utf-8")).hexdigest()[:16]
            _LOG.error(
                "[monolith c2d3e4f5a6b7] duplicate email (sha256[:16]=%s) appears %d times",
                digest,
                n,
            )
        raise RuntimeError(
            f"[monolith c2d3e4f5a6b7] ABORT: {len(dup_rows)} duplicate non-NULL "
            f"email value(s) in {_QUALIFIED}.  The UNIQUE(email) index cannot be "
            f"created.  Resolve the duplicates (offending emails logged above as "
            f"SHA-256 digests) before re-running this migration."
        )
    _LOG.info("[monolith c2d3e4f5a6b7] pre-scan PASSED — no duplicate emails.")

    # ── Step 2 — widen phone NOT NULL → NULL (always safe) ─────────────────
    op.alter_column("users", "phone", existing_type=sa.String(15), nullable=True)

    # ── Step 3 — add google_sub (nullable) ─────────────────────────────────
    op.add_column("users", sa.Column("google_sub", sa.String(255), nullable=True))

    # ── Step 4 — add auth_provider NOT NULL DEFAULT 'phone' ────────────────
    op.add_column(
        "users",
        sa.Column(
            "auth_provider",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'phone'"),
        ),
    )

    # ── Step 5 — nullable-UNIQUE index on google_sub ───────────────────────
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)

    # ── Step 6 — nullable-UNIQUE index on email (pre-scan guaranteed safe) ──
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── Step 7 — at-least-one-identity CHECK (validates immediately) ────────
    op.create_check_constraint(
        "ck_users_at_least_one_identity",
        "users",
        "phone IS NOT NULL OR google_sub IS NOT NULL",
    )

    _LOG.info(
        "[monolith c2d3e4f5a6b7] upgrade complete: phone nullable, email+google_sub "
        "UNIQUE, auth_provider added, identity CHECK in place."
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Reverse the dual-identity widening.

    REFUSES to re-tighten ``phone`` NOT NULL if any Google-only user exists.
    """
    if context.is_offline_mode():
        _LOG.info(
            "[monolith c2d3e4f5a6b7] OFFLINE DOWNGRADE — the Google-only-user guard "
            "MUST be checked manually before re-tightening phone NOT NULL."
        )
        _emit_downgrade_ddl()
        return

    conn = op.get_bind()

    google_only = conn.execute(
        sa.text(f"SELECT COUNT(*) FROM {_QUALIFIED} WHERE phone IS NULL")
    ).scalar_one()
    if google_only and int(google_only) > 0:
        raise RuntimeError(
            f"[monolith c2d3e4f5a6b7] ABORT DOWNGRADE: cannot re-tighten "
            f"{_QUALIFIED}.phone to NOT NULL — {google_only} Google-only user(s) "
            f"(phone IS NULL) exist.  Delete or assign phones to those rows "
            f"first, or stay on revision c2d3e4f5a6b7."
        )

    op.drop_constraint("ck_users_at_least_one_identity", "users", type_="check")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_column("users", "auth_provider")
    op.drop_column("users", "google_sub")
    op.alter_column("users", "phone", existing_type=sa.String(15), nullable=False)

    _LOG.info("[monolith c2d3e4f5a6b7] downgrade complete.")


# ---------------------------------------------------------------------------
# Offline DDL emitters
# ---------------------------------------------------------------------------


def _emit_upgrade_ddl() -> None:
    op.execute(sa.text(f"ALTER TABLE {_QUALIFIED} ALTER COLUMN phone DROP NOT NULL"))
    op.execute(sa.text(f"ALTER TABLE {_QUALIFIED} ADD COLUMN google_sub VARCHAR(255)"))
    op.execute(
        sa.text(
            f"ALTER TABLE {_QUALIFIED} ADD COLUMN auth_provider VARCHAR(20) "
            f"NOT NULL DEFAULT 'phone'"
        )
    )
    op.execute(
        sa.text(f"CREATE UNIQUE INDEX ix_users_google_sub ON {_QUALIFIED} (google_sub)")
    )
    op.execute(sa.text(f"CREATE UNIQUE INDEX ix_users_email ON {_QUALIFIED} (email)"))
    op.execute(
        sa.text(
            f"ALTER TABLE {_QUALIFIED} ADD CONSTRAINT ck_users_at_least_one_identity "
            f"CHECK (phone IS NOT NULL OR google_sub IS NOT NULL)"
        )
    )


def _emit_downgrade_ddl() -> None:
    op.execute(
        sa.text(
            f"ALTER TABLE {_QUALIFIED} DROP CONSTRAINT ck_users_at_least_one_identity"
        )
    )
    op.execute(sa.text("DROP INDEX public.ix_users_email"))
    op.execute(sa.text("DROP INDEX public.ix_users_google_sub"))
    op.execute(sa.text(f"ALTER TABLE {_QUALIFIED} DROP COLUMN auth_provider"))
    op.execute(sa.text(f"ALTER TABLE {_QUALIFIED} DROP COLUMN google_sub"))
    op.execute(sa.text(f"ALTER TABLE {_QUALIFIED} ALTER COLUMN phone SET NOT NULL"))
