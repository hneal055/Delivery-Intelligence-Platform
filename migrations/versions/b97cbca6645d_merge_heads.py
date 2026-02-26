"""merge_heads

Revision ID: b97cbca6645d
Revises: b2c2c9c62fe5, a1b2c3d4e5f6
Create Date: 2026-02-26 13:21:57.383997

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b97cbca6645d'
down_revision: Union[str, None] = ('b2c2c9c62fe5', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
