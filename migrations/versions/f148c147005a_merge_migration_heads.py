"""merge migration heads

Revision ID: f148c147005a
Revises: b97cbca6645d, c9d8e7f6a5b4
Create Date: 2026-08-06 08:09:01.653156

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f148c147005a'
down_revision: Union[str, None] = ('b97cbca6645d', 'c9d8e7f6a5b4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
