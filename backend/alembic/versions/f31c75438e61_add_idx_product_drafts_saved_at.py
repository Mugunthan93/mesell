"""add_idx_product_drafts_saved_at

G10 (index part): Add idx_product_drafts_saved_at on product_drafts.saved_at.

This index is the performance foundation for the future TTL cleanup task:
  DELETE FROM product_drafts WHERE saved_at < NOW() - INTERVAL '30 days'

Without this index, that query is a full sequential scan.  The index lands
now because it is useful for ANY query against saved_at (e.g. staleness
dashboards, manual cleanup runs during V1).  The Celery beat task that
drives the deletion is a services-builder deliverable once the TTL value
is confirmed by the founder.

See: docs/MVP_ARCHITECTURE_GAP_ANALYSIS.md §G10
     docs/MVP_ARCHITECTURE_GAP_DATABASE.md §G10

Revision ID: f31c75438e61
Revises: a1b2c3d4e5f6
Create Date: 2026-06-05 07:35:43.556472
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f31c75438e61"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_product_drafts_saved_at",
        "product_drafts",
        ["saved_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_product_drafts_saved_at", table_name="product_drafts")
