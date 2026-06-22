"""add_category_monitor_wave1_snapshots_notifications_product_flags_subscription_view

Category monitor Wave 1 — additive schema only. Zero V1 surface regression.

New tables:
    - category_snapshots   (diff source-of-truth; FK→categories CASCADE)
    - notifications        (idempotent fan-out; FK→users CASCADE, FK→categories CASCADE)

Existing table modifications:
    - products: +needs_recheck, +needs_reprice, +needs_export (Boolean, NOT NULL, false)

New VIEW (raw DDL only — not modelled as ORM table per spec):
    - category_subscription   (UNION of catalogs + products keyed by category)

Down_revision: e9415bdcae20 (merge razorpay billing + develop heads)

Revision ID: 480c10b0219f
Revises: e9415bdcae20
Create Date: 2026-06-22 15:05:18.957030

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '480c10b0219f'
down_revision: Union[str, None] = 'e9415bdcae20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. category_snapshots ────────────────────────────────────────────────
    op.create_table(
        'category_snapshots',
        sa.Column(
            'id',
            sa.UUID(),
            server_default=sa.text('gen_random_uuid()'),
            nullable=False,
        ),
        sa.Column(
            'category_id',
            sa.UUID(),
            nullable=False,
            comment='Category this snapshot captures',
        ),
        sa.Column(
            'captured_at',
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text('NOW()'),
            nullable=False,
            comment='Timestamp when the scrape ran',
        ),
        sa.Column(
            'content_hash',
            sa.String(length=64),
            nullable=False,
            comment='Hex content hash — equality check short-circuits diff/fan-out',
        ),
        sa.Column(
            'dimensions_jsonb',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
            comment='Captured category rule dimensions for diff engine input',
        ),
        sa.Column(
            'blob_uri',
            sa.Text(),
            nullable=True,
            comment='GCS object URI for the raw snapshot blob, NULL until upload completes',
        ),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    # Load-bearing composite: (category_id, captured_at DESC) for latest-snapshot lookup.
    # Leftmost-prefix covers category_id-only seeks — no redundant single-column index needed.
    op.create_index(
        'idx_category_snapshot_latest',
        'category_snapshots',
        ['category_id', 'captured_at'],
        unique=False,
        postgresql_using='btree',
    )

    # ── 2. notifications ─────────────────────────────────────────────────────
    op.create_table(
        'notifications',
        sa.Column(
            'id',
            sa.UUID(),
            server_default=sa.text('gen_random_uuid()'),
            nullable=False,
        ),
        sa.Column(
            'user_id',
            sa.UUID(),
            nullable=False,
            comment='Seller this notification targets',
        ),
        sa.Column(
            'category_id',
            sa.UUID(),
            nullable=False,
            comment='Category whose change triggered this notification',
        ),
        sa.Column(
            'content_hash',
            sa.String(length=64),
            nullable=False,
            comment='Hash of the snapshot that triggered this notification — part of idempotency key',
        ),
        sa.Column(
            'payload_jsonb',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
            comment='Diff summary payload for the in-app bell',
        ),
        sa.Column(
            'is_read',
            sa.Boolean(),
            server_default=sa.text('false'),
            nullable=False,
            comment='User has dismissed/read this notification',
        ),
        sa.Column(
            'read_at',
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            comment='Timestamp when the user read the notification, NULL if unread',
        ),
        sa.Column(
            'created_at',
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        # Idempotency: fan-out uses INSERT ... ON CONFLICT DO NOTHING on this key.
        sa.UniqueConstraint(
            'user_id',
            'category_id',
            'content_hash',
            name='uq_notification_user_cat_hash',
        ),
    )
    # Bell unread-count query: SELECT COUNT(*) WHERE user_id=X AND is_read=false.
    op.create_index(
        'idx_notification_user_unread',
        'notifications',
        ['user_id', 'is_read'],
        unique=False,
    )

    # ── 3. products — three flag columns (server_default self-backfills) ─────
    op.add_column(
        'products',
        sa.Column(
            'needs_recheck',
            sa.Boolean(),
            server_default=sa.text('false'),
            nullable=False,
            comment='Category compliance fields changed; seller should review this product',
        ),
    )
    op.add_column(
        'products',
        sa.Column(
            'needs_reprice',
            sa.Boolean(),
            server_default=sa.text('false'),
            nullable=False,
            comment='Category shipping/cost fields changed; seller should re-price',
        ),
    )
    op.add_column(
        'products',
        sa.Column(
            'needs_export',
            sa.Boolean(),
            server_default=sa.text('false'),
            nullable=False,
            comment='Any rule change alters XLSX output; seller should re-export',
        ),
    )

    # ── 4. category_subscription VIEW ────────────────────────────────────────
    # Director-resolved design flag (1): UNION of catalog-level + product-level
    # subscriptions.  catalogs.category_id is nullable so WHERE IS NOT NULL is
    # required on that branch; products.category_id is NOT NULL + excludes soft-deletes.
    # NOT modelled as an ORM table per spec (§5.E locked flat dir rule).
    op.execute(
        """
        CREATE VIEW category_subscription AS
        SELECT DISTINCT c.user_id, c.category_id, c.id AS catalog_id
        FROM catalogs c
        WHERE c.category_id IS NOT NULL
        UNION
        SELECT DISTINCT p.user_id, p.category_id, p.catalog_id
        FROM products p
        WHERE p.deleted_at IS NULL
        """
    )


def downgrade() -> None:
    # Exact reverse of upgrade — VIEW first, then flag columns, then tables + indexes.

    # ── 4. DROP VIEW ─────────────────────────────────────────────────────────
    op.execute("DROP VIEW IF EXISTS category_subscription")

    # ── 3. products — drop flag columns ──────────────────────────────────────
    op.drop_column('products', 'needs_export')
    op.drop_column('products', 'needs_reprice')
    op.drop_column('products', 'needs_recheck')

    # ── 2. notifications ─────────────────────────────────────────────────────
    op.drop_index('idx_notification_user_unread', table_name='notifications')
    op.drop_table('notifications')

    # ── 1. category_snapshots ────────────────────────────────────────────────
    # Note: op.drop_index does NOT accept postgresql_using — autogenerate bug; omit.
    op.drop_index('idx_category_snapshot_latest', table_name='category_snapshots')
    op.drop_table('category_snapshots')
