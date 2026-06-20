"""merge razorpay billing + develop heads

Revision ID: e9415bdcae20
Revises: d4e5f6a7b8c9, f8fa7a36383f
Create Date: 2026-06-20 10:04:52.174913

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9415bdcae20'
down_revision: Union[str, None] = ('d4e5f6a7b8c9', 'f8fa7a36383f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
