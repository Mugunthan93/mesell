"""Add Google identity to iam.users (dual-identity: phone OR Google).

google-auth feature (2026-06-18) — svc-iam chain.

This migration widens the identity model on ``iam.users`` to support Google
Sign-In as an additive identity provider (CLAUDE.md Key Decision #5 amendment;
GOOGLE_AUTH_DESIGN_BACKEND.md §B).

Schema changes
--------------
1. ``phone``        NOT NULL → NULL-able  (Google-only users have no phone).
2. ``email``        gains a nullable-UNIQUE index (now a linking key).
3. ``google_sub``   NEW  VARCHAR(255), nullable-UNIQUE (Google stable subject).
4. ``auth_provider`` NEW  VARCHAR(20) NOT NULL DEFAULT 'phone' (audit column).
5. CHECK ``ck_users_at_least_one_identity`` — ``phone IS NOT NULL OR
   google_sub IS NOT NULL``.

Upgrade safety
--------------
* Widening ``phone`` NOT NULL → NULL is always safe (no row violates it).
* Adding UNIQUE on ``email`` could fail on legacy duplicate emails, so a
  **pre-scan aborts the migration** (mirrors the Risk#5 pre-scan pattern in
  b1c2d3e4f5a6) if any non-NULL email is duplicated.  Offending emails are
  emitted to the log as SHA-256 digests (PII-safe).
* ``google_sub`` is brand-new (all NULL) → no collision possible.
* The CHECK validates immediately: every existing row has a phone.

Downgrade safety
----------------
The downgrade re-tightens ``phone`` to NOT NULL.  This **destroys** the
at-least-one-identity invariant if any Google-only user (``phone IS NULL``)
exists.  The downgrade therefore **guards**: it counts NULL-phone rows and
RAISES with a clear forensic message if any exist.  This is the correct,
honest behaviour — a downgrade that would orphan identities must not silently
proceed.

V1.5 evolution path
-------------------
When a third provider (Apple, email-magic-link) or multiple-emails-per-user is
required, normalize the inline identities into
``iam.identities(user_id, provider, provider_subject, email, verified_at)``
with a UNIQUE ``(provider, provider_subject)``.  The backfill is one identity
row per non-NULL ``phone`` / ``google_sub``.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
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
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOG = logging.getLogger("alembic.runtime.migration")

# svc-iam: users live in schema 'iam' (moved by b1c2d3e4f5a6).
_SCHEMA = "iam"
_QUALIFIED = f"{_SCHEMA}.users"


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Widen iam.users for dual-identity (phone OR Google)."""
    if context.is_offline_mode():
        _LOG.info(
            "[svc-iam c2d3e4f5a6b7] OFFLINE MODE — the duplicate-email pre-scan "
            "MUST be run manually before applying.  Emitting raw DDL."
        )
        _emit_upgrade_ddl()
        return

    conn = op.get_bind()

    # ── Step 1 — duplicate-email pre-scan (Risk-style abort guard) ──────────
    _LOG.info(
        "[svc-iam c2d3e4f5a6b7] pre-scan: checking for duplicate non-NULL emails "
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
                "[svc-iam c2d3e4f5a6b7] duplicate email (sha256[:16]=%s) appears %d times",
                digest,
                n,
            )
        raise RuntimeError(
            f"[svc-iam c2d3e4f5a6b7] ABORT: {len(dup_rows)} duplicate non-NULL "
            f"email value(s) in {_QUALIFIED}.  The UNIQUE(email) index cannot be "
            f"created.  Resolve the duplicates (offending emails logged above as "
            f"SHA-256 digests) before re-running this migration."
        )
    _LOG.info("[svc-iam c2d3e4f5a6b7] pre-scan PASSED — no duplicate emails.")

    # ── Step 2 — widen phone NOT NULL → NULL (always safe) ─────────────────
    op.alter_column(
        "users", "phone", existing_type=sa.String(15), nullable=True, schema=_SCHEMA
    )

    # ── Step 3 — add google_sub (nullable) ─────────────────────────────────
    op.add_column(
        "users", sa.Column("google_sub", sa.String(255), nullable=True), schema=_SCHEMA
    )

    # ── Step 4 — add auth_provider NOT NULL DEFAULT 'phone' ────────────────
    op.add_column(
        "users",
        sa.Column(
            "auth_provider",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'phone'"),
        ),
        schema=_SCHEMA,
    )

    # ── Step 5 — nullable-UNIQUE index on google_sub ───────────────────────
    op.create_index(
        "ix_users_google_sub", "users", ["google_sub"], unique=True, schema=_SCHEMA
    )

    # ── Step 6 — nullable-UNIQUE index on email (pre-scan guaranteed safe) ──
    op.create_index("ix_users_email", "users", ["email"], unique=True, schema=_SCHEMA)

    # ── Step 7 — at-least-one-identity CHECK (validates immediately) ────────
    op.create_check_constraint(
        "ck_users_at_least_one_identity",
        "users",
        "phone IS NOT NULL OR google_sub IS NOT NULL",
        schema=_SCHEMA,
    )

    _LOG.info(
        "[svc-iam c2d3e4f5a6b7] upgrade complete: phone nullable, email+google_sub "
        "UNIQUE, auth_provider added, identity CHECK in place."
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Reverse the dual-identity widening.

    REFUSES to re-tighten ``phone`` NOT NULL if any Google-only user exists,
    since that would destroy the at-least-one-identity invariant.
    """
    if context.is_offline_mode():
        _LOG.info(
            "[svc-iam c2d3e4f5a6b7] OFFLINE DOWNGRADE — the Google-only-user guard "
            "MUST be checked manually before re-tightening phone NOT NULL."
        )
        _emit_downgrade_ddl()
        return

    conn = op.get_bind()

    # ── Guard — refuse if Google-only users exist ──────────────────────────
    google_only = conn.execute(
        sa.text(f"SELECT COUNT(*) FROM {_QUALIFIED} WHERE phone IS NULL")
    ).scalar_one()
    if google_only and int(google_only) > 0:
        raise RuntimeError(
            f"[svc-iam c2d3e4f5a6b7] ABORT DOWNGRADE: cannot re-tighten "
            f"{_QUALIFIED}.phone to NOT NULL — {google_only} Google-only user(s) "
            f"(phone IS NULL) exist.  Delete or assign phones to those rows "
            f"first, or stay on revision c2d3e4f5a6b7."
        )

    # Reverse order of upgrade.
    op.drop_constraint(
        "ck_users_at_least_one_identity", "users", schema=_SCHEMA, type_="check"
    )
    op.drop_index("ix_users_email", table_name="users", schema=_SCHEMA)
    op.drop_index("ix_users_google_sub", table_name="users", schema=_SCHEMA)
    op.drop_column("users", "auth_provider", schema=_SCHEMA)
    op.drop_column("users", "google_sub", schema=_SCHEMA)
    op.alter_column(
        "users", "phone", existing_type=sa.String(15), nullable=False, schema=_SCHEMA
    )

    _LOG.info("[svc-iam c2d3e4f5a6b7] downgrade complete.")


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
    op.execute(sa.text(f"DROP INDEX {_SCHEMA}.ix_users_email"))
    op.execute(sa.text(f"DROP INDEX {_SCHEMA}.ix_users_google_sub"))
    op.execute(sa.text(f"ALTER TABLE {_QUALIFIED} DROP COLUMN auth_provider"))
    op.execute(sa.text(f"ALTER TABLE {_QUALIFIED} DROP COLUMN google_sub"))
    op.execute(sa.text(f"ALTER TABLE {_QUALIFIED} ALTER COLUMN phone SET NOT NULL"))
