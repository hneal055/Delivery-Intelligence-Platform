"""add pickup leg, ready-for-pickup time and exception reason to packages

A job can now be pickup -> delivery: the package records where it is
collected (geocoded like the delivery address), when the shipper said it is
ready, and why a driver could not complete it.

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-10-11 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4b5c6d7e8f9'
down_revision: Union[str, None] = 'f3a4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('packages', sa.Column('pickup_address', sa.String(), nullable=True))
    op.add_column('packages', sa.Column('pickup_lat', sa.Float(), nullable=True))
    op.add_column('packages', sa.Column('pickup_lon', sa.Float(), nullable=True))
    op.add_column('packages', sa.Column('pickup_instructions', sa.Text(), nullable=True))
    op.add_column('packages', sa.Column('ready_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('packages', sa.Column('exception_reason', sa.Text(), nullable=True))


def downgrade() -> None:
    for column in ('exception_reason', 'ready_at', 'pickup_instructions',
                   'pickup_lon', 'pickup_lat', 'pickup_address'):
        op.drop_column('packages', column)
