"""pricing_calcs forward-estimator additive columns

§12.M AMENDMENT 2026-06-18 — Price Calculator forward-estimator rework
(founder-ratified).

ADDITIVE + reversible.  Adds 12 nullable breakdown columns to
``pricing_calcs`` for the forward payout estimator:

  estimated_payout, referral_commission, shipping_charge, logistics_fee,
  fixed_fee, gst_on_fees, tcs, tds, rto_expected_loss, return_rate_pct,
  markup_pct, wdrp_price

All columns are NULLABLE so the migration is purely additive over existing
rows.  The legacy ``commission_pct`` column is RE-PURPOSED as the
seller-entered commission snapshot — no DDL change to that column is
needed (only a semantic re-purpose), so it is not touched here.

See: docs/BACKEND_ARCHITECTURE.md §12.M (5)
     docs/V1_FEATURE_SPEC.md Feature 7 AMENDMENT 2026-06-18

Revision ID: b7c2e1a9d3f4
Revises: f31c75438e61
Create Date: 2026-06-18 10:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b7c2e1a9d3f4"
down_revision: Union[str, None] = "f31c75438e61"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (column_name, type) — all nullable, additive.
_NEW_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("estimated_payout", sa.Numeric(10, 2)),
    ("referral_commission", sa.Numeric(10, 2)),
    ("shipping_charge", sa.Numeric(10, 2)),
    ("logistics_fee", sa.Numeric(10, 2)),
    ("fixed_fee", sa.Numeric(10, 2)),
    ("gst_on_fees", sa.Numeric(10, 2)),
    ("tcs", sa.Numeric(10, 2)),
    ("tds", sa.Numeric(10, 2)),
    ("rto_expected_loss", sa.Numeric(10, 2)),
    ("return_rate_pct", sa.Numeric(5, 2)),
    ("markup_pct", sa.Numeric(5, 2)),
    ("wdrp_price", sa.Numeric(10, 2)),
)


def upgrade() -> None:
    for name, type_ in _NEW_COLUMNS:
        op.add_column(
            "pricing_calcs",
            sa.Column(name, type_, nullable=True),
        )


def downgrade() -> None:
    # Drop in reverse order for symmetry.
    for name, _type in reversed(_NEW_COLUMNS):
        op.drop_column("pricing_calcs", name)
