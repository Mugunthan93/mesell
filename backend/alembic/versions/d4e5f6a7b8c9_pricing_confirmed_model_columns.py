"""pricing_calcs — W2 confirmed-model settlement columns

Additive migration for the Price Calculator rework (W2, 2026-06-19).

Adds 7 new nullable columns implementing the census-verified settlement
formula (project_pricing_transfer_price_model.md):

    selling_price          NUMERIC(10,2)
    shipping               NUMERIC(10,2)
    total_price            NUMERIC(10,2)
    commission_fees        NUMERIC(10,2)
    gst_on_shipping        NUMERIC(10,2)
    estimated_bank_settlement NUMERIC(10,2)
    meesho_leaf_id         VARCHAR(16)

NOTE — tcs and tds are NOT added here: they already exist on the table from
migration b7c2e1a9d3f4 (PR #285 forward-estimator).  The confirmed model
adopts those two columns with corrected semantics; no DDL change needed.
commission_pct likewise exists since the baseline migration 935e55b4852c.

All 7 new columns are nullable so existing rows (all NULL) are unaffected.
The W2+ service layer writes ONLY these columns (+ tcs, tds, commission_pct
reused) and NEVER writes the deprecated #285 columns.

downgrade() drops only the 7 columns introduced here; it does NOT touch the
#285 columns or tcs/tds (those are owned by their respective revisions).

Math reference:
    total_price               = selling_price + shipping
    gst_on_shipping           = 0.18 x shipping
    tds                       = 0.001 x total_price
    tcs                       = 0 (always)
    commission_fees           = commission_pct x selling_price
    estimated_bank_settlement = selling_price - commission_fees
                                - gst_on_shipping - tds - tcs

Revision ID: d4e5f6a7b8c9
Revises: c2d3e4f5a6b7
Create Date: 2026-06-19 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# New columns — (name, SQLAlchemy type)
# tcs + tds already exist from b7c2e1a9d3f4; NOT listed here.
# commission_pct already exists from baseline 935e55b4852c; NOT listed here.
# ---------------------------------------------------------------------------

_NEW_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("selling_price", sa.Numeric(10, 2)),
    ("shipping", sa.Numeric(10, 2)),
    ("total_price", sa.Numeric(10, 2)),
    ("commission_fees", sa.Numeric(10, 2)),
    ("gst_on_shipping", sa.Numeric(10, 2)),
    ("estimated_bank_settlement", sa.Numeric(10, 2)),
    ("meesho_leaf_id", sa.String(16)),
)


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Add 7 confirmed-model settlement columns to pricing_calcs (all nullable)."""
    for col_name, col_type in _NEW_COLUMNS:
        op.add_column(
            "pricing_calcs",
            sa.Column(col_name, col_type, nullable=True),
        )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Drop the 7 confirmed-model columns added by this revision only."""
    for col_name, _col_type in reversed(_NEW_COLUMNS):
        op.drop_column("pricing_calcs", col_name)
