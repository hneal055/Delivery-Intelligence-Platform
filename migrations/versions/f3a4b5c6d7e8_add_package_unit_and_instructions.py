"""add package dest_unit and delivery_instructions

Suite/floor/dock and driver-facing delivery instructions (e.g. "leave with
concierge"). Both are shown on the driver's phone; job notes are not.

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-10-11 08:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a4b5c6d7e8'
down_revision: Union[str, None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('packages', sa.Column('dest_unit', sa.String(), nullable=True))
    op.add_column('packages', sa.Column('delivery_instructions', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('packages', 'delivery_instructions')
    op.drop_column('packages', 'dest_unit')
