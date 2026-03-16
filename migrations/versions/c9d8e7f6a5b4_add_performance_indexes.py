"""add performance indexes — composite, partial, and spatial

Revision ID: c9d8e7f6a5b4
Revises: a1b2c3d4e5f6
Create Date: 2026-03-16 00:00:00.000000

Adds indexes covering the highest-frequency query patterns identified
during production readiness review:

  packages:
    - (driver_id, status)        — "find this driver's pending packages"
    - (status)                   — "all packages in state X"
    - (created_at DESC)          — time-ordered scans / analytics

  location_history:
    - (driver_id, timestamp DESC) — "latest N fixes for driver D"

  drivers:
    - (status)                   — "active / available drivers"

  dispatch_jobs:
    - (driver_id, status)        — "open jobs for driver D"
    - (status, scheduled_at)     — "upcoming pending jobs"

  driver_availability:
    - (driver_id, date)          — "is driver D available on date X?"

  depots:
    - GIST on location           — spatial proximity queries
"""

from alembic import op
import geoalchemy2
import sqlalchemy as sa

revision: str = "c9d8e7f6a5b4"
down_revision: str = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── packages ─────────────────────────────────────────────────────────────
    op.create_index(
        "idx_packages_driver_status",
        "packages",
        ["driver_id", "status"],
    )
    op.create_index(
        "idx_packages_status",
        "packages",
        ["status"],
    )
    # Partial index: only index rows that are not yet delivered (common hot path)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_packages_active "
        "ON packages (driver_id, created_at DESC) "
        "WHERE status NOT IN ('delivered', 'cancelled')"
    )
    op.create_index(
        "idx_packages_created_at",
        "packages",
        [sa.text("created_at DESC")],
        postgresql_using="btree",
    )

    # ── location_history ─────────────────────────────────────────────────────
    # Composite index lets Postgres satisfy "ORDER BY timestamp DESC LIMIT N"
    # for a given driver purely from the index.
    op.create_index(
        "idx_location_history_driver_ts",
        "location_history",
        ["driver_id", sa.text("timestamp DESC")],
        postgresql_using="btree",
    )

    # ── drivers ──────────────────────────────────────────────────────────────
    op.create_index(
        "idx_drivers_status",
        "drivers",
        ["status"],
    )

    # ── dispatch_jobs ────────────────────────────────────────────────────────
    op.create_index(
        "idx_dispatch_jobs_driver_status",
        "dispatch_jobs",
        ["driver_id", "status"],
    )
    op.create_index(
        "idx_dispatch_jobs_status_scheduled",
        "dispatch_jobs",
        ["status", "scheduled_at"],
    )

    # ── driver_availability ──────────────────────────────────────────────────
    op.create_index(
        "idx_driver_availability_driver_date",
        "driver_availability",
        ["driver_id", "date"],
    )

    # ── depots (spatial) ─────────────────────────────────────────────────────
    # GIST index on depot geometry — missing from the advanced-routing migration.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_depots_location "
        "ON depots USING gist (location)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_depots_location")
    op.drop_index("idx_driver_availability_driver_date", table_name="driver_availability")
    op.drop_index("idx_dispatch_jobs_status_scheduled", table_name="dispatch_jobs")
    op.drop_index("idx_dispatch_jobs_driver_status", table_name="dispatch_jobs")
    op.drop_index("idx_drivers_status", table_name="drivers")
    op.drop_index("idx_location_history_driver_ts", table_name="location_history")
    op.drop_index("idx_packages_created_at", table_name="packages")
    op.execute("DROP INDEX IF EXISTS idx_packages_active")
    op.drop_index("idx_packages_status", table_name="packages")
    op.drop_index("idx_packages_driver_status", table_name="packages")
