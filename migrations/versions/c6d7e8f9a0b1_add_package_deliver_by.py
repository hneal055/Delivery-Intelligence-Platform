"""add deliver_by (promised delivery time) to packages

The time the customer was promised. Drives the "late" and "due soon"
alerts on the dashboard and the on-time rate.

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-10-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6d7e8f9a0b1'
down_revision: Union[str, None] = 'b5c6d7e8f9a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('packages', sa.Column('deliver_by', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('packages', 'deliver_by')
