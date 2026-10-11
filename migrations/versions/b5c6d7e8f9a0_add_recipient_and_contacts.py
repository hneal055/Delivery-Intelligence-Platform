"""add recipient / pickup contact to packages and received_by to proofs

Who to ask for and call at each end of a job, and the name of the person
who actually took the package (recorded on the proof of delivery).

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-10-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5c6d7e8f9a0'
down_revision: Union[str, None] = 'a4b5c6d7e8f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for column in ('recipient_name', 'recipient_phone', 'pickup_contact_name', 'pickup_contact_phone'):
        op.add_column('packages', sa.Column(column, sa.String(), nullable=True))
    op.add_column('delivery_proofs', sa.Column('received_by', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('delivery_proofs', 'received_by')
    for column in ('pickup_contact_phone', 'pickup_contact_name', 'recipient_phone', 'recipient_name'):
        op.drop_column('packages', column)
