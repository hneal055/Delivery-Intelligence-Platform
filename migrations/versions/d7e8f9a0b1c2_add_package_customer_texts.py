"""record when the customer was texted about a package

One text per event: "out for delivery" when the driver picks it up and
"delivered" when it is confirmed. The timestamps stop a re-scan or a
resent confirmation from texting the customer twice.

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-10-12 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7e8f9a0b1c2'
down_revision: Union[str, None] = 'c6d7e8f9a0b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('packages', sa.Column('texted_out_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('packages', sa.Column('texted_delivered_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('packages', 'texted_delivered_at')
    op.drop_column('packages', 'texted_out_at')
