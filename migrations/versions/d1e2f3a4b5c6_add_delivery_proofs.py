"""add delivery_proofs

Stores each accepted proof of delivery (who, when, where, photo key and
signature) in Postgres. Replaces the old SQLite delivery_proofs table.
Hand-written: autogenerate would also pick up unrelated drift.

Revision ID: d1e2f3a4b5c6
Revises: 9b1caccd01d4
Create Date: 2026-10-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = '9b1caccd01d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('delivery_proofs',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('package_id', sa.String(), nullable=False),
    sa.Column('driver_id', sa.String(), nullable=False),
    sa.Column('photo_key', sa.String(), nullable=False),
    sa.Column('signature_svg', sa.Text(), nullable=True),
    sa.Column('lat', sa.Float(), nullable=True),
    sa.Column('lon', sa.Float(), nullable=True),
    sa.Column('distance_m', sa.Float(), nullable=True),
    sa.Column('captured_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['package_id'], ['packages.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_proofs_package_id'), 'delivery_proofs', ['package_id'], unique=False)
    op.create_index(op.f('ix_delivery_proofs_driver_id'), 'delivery_proofs', ['driver_id'], unique=False)
    op.create_index(op.f('ix_delivery_proofs_captured_at'), 'delivery_proofs', ['captured_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_delivery_proofs_captured_at'), table_name='delivery_proofs')
    op.drop_index(op.f('ix_delivery_proofs_driver_id'), table_name='delivery_proofs')
    op.drop_index(op.f('ix_delivery_proofs_package_id'), table_name='delivery_proofs')
    op.drop_table('delivery_proofs')
