"""create audit_logs table

Revision ID: 843ff67f0108
Revises: f148c147005a
Create Date: 2026-08-06 08:10:01.105687

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "843ff67f0108"
down_revision: Union[str, None] = "f148c147005a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(
        "audit_logs",

        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            "timestamp_utc",
            sa.DateTime(),
            nullable=False,
        ),

        sa.Column(
            "actor_email",
            sa.String(255),
            nullable=False,
        ),

        sa.Column(
            "actor_role",
            sa.String(50),
            nullable=True,
        ),

        sa.Column(
            "action",
            sa.String(100),
            nullable=False,
        ),

        sa.Column(
            "target_user",
            sa.String(255),
            nullable=True,
        ),

        sa.Column(
            "details",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "ip_address",
            sa.String(50),
            nullable=True,
        ),

        sa.Column(
            "session_id",
            sa.String(255),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
    )

    op.create_index(
        "idx_audit_logs_timestamp",
        "audit_logs",
        ["timestamp_utc"],
    )

    op.create_index(
        "idx_audit_logs_action",
        "audit_logs",
        ["action"],
    )

    op.create_index(
        "idx_audit_logs_actor_email",
        "audit_logs",
        ["actor_email"],
    )

    op.create_index(
        "idx_audit_logs_target_user",
        "audit_logs",
        ["target_user"],
    )


def downgrade() -> None:

    op.drop_index(
        "idx_audit_logs_target_user",
        table_name="audit_logs",
    )

    op.drop_index(
        "idx_audit_logs_actor_email",
        table_name="audit_logs",
    )

    op.drop_index(
        "idx_audit_logs_action",
        table_name="audit_logs",
    )

    op.drop_index(
        "idx_audit_logs_timestamp",
        table_name="audit_logs",
    )

    op.drop_table("audit_logs")
    class AuditLog(Base):