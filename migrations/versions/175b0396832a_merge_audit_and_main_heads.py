"""merge_audit_and_main_heads

Revision ID: 175b0396832a
Revises: 843ff67f0108, f148c147005a
Create Date: 2026-08-31 10:57:03.229384

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '175b0396832a'
down_revision: Union[str, None] = ('843ff67f0108', 'f148c147005a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
