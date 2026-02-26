# ==========================================
# FILE: migrations/versions/xxxx_add_advanced_routing_tables.py
# Database migration for advanced routing
# ==========================================

"""add advanced routing tables

Revision ID: a1b2c3d4e5f6
Revises: e647f96280c3
Create Date: 2026-02-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "e647f96280c3"
branch_labels = None
depends_on = None


def upgrade():
    # Depots table
    op.create_table(
        "depots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("location", geoalchemy2.Geometry("POINT", srid=4326), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("operating_hours_start", sa.Time(), nullable=True),
        sa.Column("operating_hours_end", sa.Time(), nullable=True),
        sa.Column("max_vehicles", sa.Integer(), nullable=True, server_default="50"),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_depots_active", "depots", ["is_active"])

    # Vehicle Profiles table
    op.create_table(
        "vehicle_profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("vehicle_id", sa.String(), nullable=False),
        sa.Column("max_weight_kg", sa.Float(), nullable=True, server_default="1000.0"),
        sa.Column("max_volume_m3", sa.Float(), nullable=True, server_default="10.0"),
        sa.Column("max_packages", sa.Integer(), nullable=True, server_default="100"),
        sa.Column("vehicle_type", sa.String(), nullable=True, server_default="van"),
        sa.Column("fuel_type", sa.String(), nullable=True, server_default="gasoline"),
        sa.Column("avg_speed_kmh", sa.Float(), nullable=True, server_default="45.0"),
        sa.Column(
            "has_refrigeration", sa.Boolean(), nullable=True, server_default="false"
        ),
        sa.Column("has_lift_gate", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("special_capabilities", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vehicle_id"),
    )
    op.create_index(
        "idx_vehicle_profiles_vehicle_id", "vehicle_profiles", ["vehicle_id"]
    )

    # Route History table
    op.create_table(
        "route_history",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "driver_id", sa.String(), sa.ForeignKey("drivers.id"), nullable=False
        ),
        sa.Column("depot_id", sa.String(), sa.ForeignKey("depots.id"), nullable=True),
        sa.Column("total_distance_km", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column(
            "total_duration_minutes", sa.Float(), nullable=True, server_default="0.0"
        ),
        sa.Column(
            "total_service_time_minutes",
            sa.Float(),
            nullable=True,
            server_default="0.0",
        ),
        sa.Column("stops_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estimated_end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "capacity_utilization_percent",
            sa.Float(),
            nullable=True,
            server_default="0.0",
        ),
        sa.Column(
            "time_window_violations", sa.Integer(), nullable=True, server_default="0"
        ),
        sa.Column("stops_sequence", postgresql.JSON, nullable=True),
        sa.Column("break_times", postgresql.JSON, nullable=True),
        sa.Column("route_geometry", postgresql.JSON, nullable=True),
        sa.Column(
            "optimization_objective",
            sa.String(),
            nullable=True,
            server_default="minimize_distance",
        ),
        sa.Column(
            "was_reoptimized", sa.Boolean(), nullable=True, server_default="false"
        ),
        sa.Column(
            "reoptimization_count", sa.Integer(), nullable=True, server_default="0"
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_route_history_driver", "route_history", ["driver_id"])
    op.create_index("idx_route_history_depot", "route_history", ["depot_id"])
    op.create_index("idx_route_history_start_time", "route_history", ["start_time"])

    # Driver Break Logs table
    op.create_table(
        "driver_break_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "driver_id", sa.String(), sa.ForeignKey("drivers.id"), nullable=False
        ),
        sa.Column(
            "route_id", sa.String(), sa.ForeignKey("route_history.id"), nullable=True
        ),
        sa.Column("break_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("break_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("break_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("break_location_lat", sa.Float(), nullable=True),
        sa.Column("break_location_lon", sa.Float(), nullable=True),
        sa.Column(
            "break_location", geoalchemy2.Geometry("POINT", srid=4326), nullable=True
        ),
        sa.Column("break_type", sa.String(), nullable=True, server_default="scheduled"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_break_logs_driver", "driver_break_logs", ["driver_id"])

    # Time Window Constraints table
    op.create_table(
        "time_window_constraints",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "package_id", sa.String(), sa.ForeignKey("packages.id"), nullable=False
        ),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_hard_constraint", sa.Boolean(), nullable=True, server_default="true"
        ),
        sa.Column("estimated_arrival", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_arrival", sa.DateTime(timezone=True), nullable=True),
        sa.Column("was_violated", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("package_id"),
    )
    op.create_index(
        "idx_time_windows_package", "time_window_constraints", ["package_id"]
    )


def downgrade():
    op.drop_table("time_window_constraints")
    op.drop_table("driver_break_logs")
    op.drop_table("route_history")
    op.drop_table("vehicle_profiles")
    op.drop_table("depots")
