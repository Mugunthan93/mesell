"""add billing tables subscriptions payments webhook_events + widen users.plan check + add users.trial_ends_at

Razorpay Integration — Wave 1 (data model only).
Session: mesell-razorpay-integration-backend-session-1
Date: 2026-06-19

Tables created:
  - subscriptions  (RAZORPAY_INTEGRATION_SPEC §7.1)
  - payments       (RAZORPAY_INTEGRATION_SPEC §7.2; amounts in paise per F9)
  - webhook_events (RAZORPAY_INTEGRATION_SPEC §7.3; string PK — dedupe gate)

users changes:
  - ADD COLUMN trial_ends_at TIMESTAMPTZ NULL (§7.4a — app-side Pro trial)
  - ADD CONSTRAINT ck_users_plan CHECK(plan IN (...)) — Pricing v2 full vocabulary
  - Update plan column comment to reflect widened vocabulary

DEVIATION from WAVE1_DB_TASKSPEC.md §0:
  The task spec stated down_revision = 'b7c2e1a9d3f4'.  The ACTUAL single head
  at build time is 'c2d3e4f5a6b7' (google identity migration, merged to develop
  after the spec was authored).  Using c2d3e4f5a6b7 avoids head divergence.
  Flagged in PR per spec §0 instructions.

Revision ID: f8fa7a36383f
Revises: c2d3e4f5a6b7
Create Date: 2026-06-19 00:29:11.901723
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "f8fa7a36383f"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Create billing tables and extend users for Razorpay Wave 1.

    Operation order:
      1. subscriptions  (FKs only to users; must precede payments)
      2. subscriptions indexes (hot entitlement + partial unique active-guard)
      3. payments       (FKs to subscriptions + users)
      4. payments indexes
      5. webhook_events (standalone — no FKs)
      6. webhook_events indexes
      7. users.trial_ends_at column add
      8. ck_users_plan CHECK constraint add
      9. users.plan column comment update (cosmetic — no DDL lock required)
    """

    # ── 1. Create subscriptions ─────────────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant owner — RESTRICT so billing records survive user soft-delete",
        ),
        sa.Column(
            "razorpay_subscription_id",
            sa.String(255),
            nullable=True,
            comment="Razorpay sub id — NULL for LTD Orders path (multiple NULLs allowed)",
        ),
        sa.Column(
            "razorpay_order_id",
            sa.String(255),
            nullable=True,
            comment="Razorpay order id — set only for LTD one-time purchase",
        ),
        sa.Column(
            "tier",
            sa.String(20),
            nullable=False,
            comment="Pricing v2 tier: starter|pro|pro_annual|business|business_annual|ltd",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            comment=(
                "Subscription lifecycle status — mirrors Razorpay states + "
                "MeeSell past_due (= Razorpay pending)"
            ),
        ),
        sa.Column(
            "current_period_end",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            comment="End of the current paid period; NULL = perpetual (LTD sentinel)",
        ),
        sa.Column(
            "cancel_scheduled_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Set when a cancel-at-cycle-end has been scheduled via Razorpay",
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
            comment="Updated by the service layer on every state transition",
        ),
        # CHECK: tier must be a known non-free billing tier (free is NOT a sub tier)
        sa.CheckConstraint(
            "tier IN ('starter','pro','pro_annual','business','business_annual','ltd')",
            name="ck_subscriptions_tier",
        ),
        # CHECK: status must be a known Razorpay + MeeSell lifecycle value
        sa.CheckConstraint(
            "status IN ('created','authenticated','active','past_due',"
            "'halted','cancelled','completed','expired')",
            name="ck_subscriptions_status",
        ),
        # UNIQUE: razorpay_subscription_id — NULLs allowed (NULL != NULL in PG UNIQUE)
        sa.UniqueConstraint("razorpay_subscription_id", name="uq_subscriptions_razorpay_sub_id"),
        # UNIQUE: razorpay_order_id — NULLs allowed
        sa.UniqueConstraint("razorpay_order_id", name="uq_subscriptions_razorpay_order_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 2. subscriptions indexes ────────────────────────────────────────────
    # Hot entitlement lookup: "does user X have an active subscription?"
    op.create_index(
        "idx_subscriptions_user_id_status",
        "subscriptions",
        ["user_id", "status"],
    )
    # Partial unique: at most one 'active' subscription per user.
    # Prevents a stale race between LTD + recurring both landing active.
    op.create_index(
        "uq_subscriptions_one_active_per_user",
        "subscriptions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    # ── 3. Create payments ──────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "subscription_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment=(
                "Parent subscription — nullable for LTD order payments "
                "or pre-linkage failed records"
            ),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Explicit tenant FK — billing records survive user soft-delete (RESTRICT)",
        ),
        sa.Column(
            "razorpay_payment_id",
            sa.String(255),
            nullable=True,
            comment="Razorpay payment id — nullable (may be absent on failed-before-charge records)",
        ),
        sa.Column(
            "amount_paise",
            sa.Integer,
            nullable=False,
            comment=(
                "Amount in paise (Razorpay-native), e.g. 49900 = ₹499.00.  "
                "F9 ruling: always paise, never rupees, never float."
            ),
        ),
        sa.Column(
            "currency",
            sa.String(3),
            server_default=sa.text("'INR'"),
            nullable=False,
            comment="ISO 4217 currency code — always INR for V1.5",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            comment="Payment outcome: captured | failed | refunded",
        ),
        sa.Column(
            "event_type",
            sa.String(40),
            nullable=True,
            comment=(
                "Source webhook event type, e.g. subscription.charged, "
                "payment.captured, refund.processed"
            ),
        ),
        sa.Column(
            "occurred_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Event timestamp from the Razorpay payload (distinct from created_at)",
        ),
        sa.Column(
            "raw_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Charge or refund payload slice — stored for ops triage + reconciliation",
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
            comment="Row insert time — distinct from occurred_at (the Razorpay event time)",
        ),
        # CHECK: status must be a known payment outcome
        sa.CheckConstraint(
            "status IN ('captured','failed','refunded')",
            name="ck_payments_status",
        ),
        # UNIQUE: razorpay_payment_id — NULLs allowed
        sa.UniqueConstraint("razorpay_payment_id", name="uq_payments_razorpay_payment_id"),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 4. payments indexes ─────────────────────────────────────────────────
    op.create_index("idx_payments_user_id", "payments", ["user_id"])
    op.create_index("idx_payments_subscription_id", "payments", ["subscription_id"])

    # ── 5. Create webhook_events ────────────────────────────────────────────
    op.create_table(
        "webhook_events",
        sa.Column(
            "event_id",
            sa.String(255),
            nullable=False,
            comment=(
                "Razorpay event id — natural string PK used as the ON CONFLICT dedupe key.  "
                "Not a UUID.  See RAZORPAY_INTEGRATION_SPEC §7.3."
            ),
        ),
        sa.Column(
            "event_type",
            sa.String(60),
            nullable=False,
            comment="Razorpay event type, e.g. subscription.charged, payment.captured",
        ),
        sa.Column(
            "payload_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment=(
                "Full raw webhook payload — enables replay of processed events "
                "without re-fetching from Razorpay (RAZORPAY_INTEGRATION_SPEC §4.4).  "
                "Note: may contain PII (customer email/phone); apply retention/purge policy."
            ),
        ),
        sa.Column(
            "signature_valid",
            sa.Boolean,
            nullable=False,
            comment=(
                "HMAC-SHA256 signature verified against RAZORPAY_WEBHOOK_SECRET at receipt time.  "
                "False = arrived but signature failed (logged for ops; Razorpay will retry)."
            ),
        ),
        sa.Column(
            "received_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
            comment="Wall-clock time the HTTP request was received by our webhook endpoint",
        ),
        sa.Column(
            "processed_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            comment="NULL until the event handler commits successfully; set in the same tx",
        ),
        sa.Column(
            "processing_error",
            sa.Text,
            nullable=True,
            comment="Last handler error message — used for ops triage of stuck events",
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )

    # ── 6. webhook_events indexes ───────────────────────────────────────────
    # Event-type + time bucket lookup
    op.create_index(
        "idx_webhook_events_type_received",
        "webhook_events",
        ["event_type", "received_at"],
    )
    # Partial: find stuck/unprocessed events efficiently
    op.create_index(
        "idx_webhook_events_unprocessed",
        "webhook_events",
        ["processed_at"],
        postgresql_where=sa.text("processed_at IS NULL"),
    )

    # ── 7. users.trial_ends_at ──────────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column(
            "trial_ends_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            comment=(
                "14-day Pro trial expiry (Pricing v2 §5.1).  Pro entitlement granted while "
                "now() < trial_ends_at; user stays plan='free'.  "
                "NULL = no trial granted yet or trial superseded by a paid subscription."
            ),
        ),
    )

    # ── 8. ck_users_plan CHECK ──────────────────────────────────────────────
    # Widens plan vocabulary from informal "free|pro" to the full Pricing v2 set.
    # IMPORTANT: subscriptions.tier has a DIFFERENT CHECK that EXCLUDES 'free'.
    op.create_check_constraint(
        "ck_users_plan",
        "users",
        "plan IN ('free','starter','pro','pro_annual','business','business_annual','ltd')",
    )

    # ── 9. users.plan column comment (cosmetic) ─────────────────────────────
    op.alter_column(
        "users",
        "plan",
        existing_type=sa.String(20),
        comment="free | starter | pro | pro_annual | business | business_annual | ltd",
        existing_comment="free | pro",
        existing_nullable=False,
        existing_server_default=sa.text("'free'::character varying"),
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Reverse Wave 1 billing schema changes.

    Operation order (exact reverse of upgrade):
      1. Revert users.plan column comment
      2. Drop ck_users_plan CHECK constraint
      3. Drop users.trial_ends_at column
      4. Drop webhook_events (standalone — drop first, no dependents)
      5. Drop payments (FKs to subscriptions + users — must drop before subscriptions)
      6. Drop subscriptions (last — payments FKd to it)
    """

    # ── 1. Revert users.plan comment ────────────────────────────────────────
    op.alter_column(
        "users",
        "plan",
        existing_type=sa.String(20),
        comment="free | pro",
        existing_comment="free | starter | pro | pro_annual | business | business_annual | ltd",
        existing_nullable=False,
        existing_server_default=sa.text("'free'::character varying"),
    )

    # ── 2. Drop ck_users_plan CHECK ─────────────────────────────────────────
    op.drop_constraint("ck_users_plan", "users", type_="check")

    # ── 3. Drop users.trial_ends_at ─────────────────────────────────────────
    op.drop_column("users", "trial_ends_at")

    # ── 4. Drop webhook_events (standalone) ─────────────────────────────────
    # Indexes are automatically dropped with the table in PostgreSQL.
    op.drop_table("webhook_events")

    # ── 5. Drop payments (FKs to subscriptions + users) ─────────────────────
    # Must drop before subscriptions because payments FKs to subscriptions.id.
    op.drop_table("payments")

    # ── 6. Drop subscriptions (last) ────────────────────────────────────────
    op.drop_table("subscriptions")
