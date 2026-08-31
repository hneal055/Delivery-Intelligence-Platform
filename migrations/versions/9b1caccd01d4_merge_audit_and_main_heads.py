"""merge_audit_and_main_heads

Revision ID: 9b1caccd01d4
Revises: 175b0396832a
Create Date: 2026-08-31 10:58:16.005489

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b1caccd01d4'
down_revision: Union[str, None] = '175b0396832a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
