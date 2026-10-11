"""backfill driver profiles for driver accounts

Every login account with role 'driver' needs a drivers row (id = username)
to be listed and assigned by dispatch. Accounts created before login started
creating that row (see services/driver_profile.py) get one here.

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-10-11 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO drivers (id, name, status)
        SELECT u.username, u.username, 'active'
        FROM users u
        WHERE u.role = 'driver'
          AND NOT EXISTS (SELECT 1 FROM drivers d WHERE d.id = u.username)
        """
    )


def downgrade() -> None:
    # Data-only backfill; the rows may be referenced by jobs and packages by
    # now, so they are left in place.
    pass
