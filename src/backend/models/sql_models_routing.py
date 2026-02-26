# ==========================================
# FILE: src/backend/models/sql_models_routing.py
# Database models for advanced routing
# ==========================================

from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    Boolean,
    Integer,
    ForeignKey,
    Time,
    ARRAY,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
import uuid

from src.backend.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Depot(Base):
    __tablename__ = "depots"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    location = Column(Geometry("POINT", srid=4326), nullable=True)
    address = Column(String, nullable=True)

    operating_hours_start = Column(Time, default=func.time("06:00:00"))
    operating_hours_end = Column(Time, default=func.time("22:00:00"))
    max_vehicles = Column(Integer, default=50)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    routes = relationship("RouteHistory", back_populates="depot")

    def __repr__(self):
        return f"<Depot {self.name}>"


class RouteHistory(Base):
    __tablename__ = "route_history"

    id = Column(String, primary_key=True, default=generate_uuid)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=False)
    depot_id = Column(String, ForeignKey("depots.id"), nullable=True)

    total_distance_km = Column(Float, default=0.0)
    total_duration_minutes = Column(Float, default=0.0)
    total_service_time_minutes = Column(Float, default=0.0)
    stops_count = Column(Integer, default=0)

    start_time = Column(DateTime(timezone=True), nullable=False)
    estimated_end_time = Column(DateTime(timezone=True), nullable=True)
    actual_end_time = Column(DateTime(timezone=True), nullable=True)

    capacity_utilization_percent = Column(Float, default=0.0)
    time_window_violations = Column(Integer, default=0)

    # JSON fields for complex data
    stops_sequence = Column(JSON, nullable=True)  # Array of stop IDs in order
    break_times = Column(JSON, nullable=True)  # Array of break timestamps
    route_geometry = Column(JSON, nullable=True)  # GeoJSON route

    optimization_objective = Column(String, default="minimize_distance")
    was_reoptimized = Column(Boolean, default=False)
    reoptimization_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    depot = relationship("Depot", back_populates="routes")

    def __repr__(self):
        return f"<RouteHistory {self.id} - Driver {self.driver_id}>"


class VehicleProfile(Base):
    __tablename__ = "vehicle_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    vehicle_id = Column(String, unique=True, nullable=False, index=True)

    # Capacity constraints
    max_weight_kg = Column(Float, default=1000.0)
    max_volume_m3 = Column(Float, default=10.0)
    max_packages = Column(Integer, default=100)

    # Vehicle characteristics
    vehicle_type = Column(String, default="van")  # van, truck, cargo_bike
    fuel_type = Column(String, default="gasoline")  # gasoline, diesel, electric
    avg_speed_kmh = Column(Float, default=45.0)

    # Capabilities
    has_refrigeration = Column(Boolean, default=False)
    has_lift_gate = Column(Boolean, default=False)
    special_capabilities = Column(
        ARRAY(String), nullable=True
    )  # ["fragile", "oversized"]

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<VehicleProfile {self.vehicle_id}>"


class DriverBreakLog(Base):
    __tablename__ = "driver_break_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=False, index=True)
    route_id = Column(String, ForeignKey("route_history.id"), nullable=True)

    break_start = Column(DateTime(timezone=True), nullable=False)
    break_end = Column(DateTime(timezone=True), nullable=True)
    break_duration_minutes = Column(Integer, nullable=True)

    break_location_lat = Column(Float, nullable=True)
    break_location_lon = Column(Float, nullable=True)
    break_location = Column(Geometry("POINT", srid=4326), nullable=True)

    break_type = Column(String, default="scheduled")  # scheduled, manual, regulatory

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<DriverBreak {self.driver_id} at {self.break_start}>"


class TimeWindowConstraint(Base):
    __tablename__ = "time_window_constraints"

    id = Column(String, primary_key=True, default=generate_uuid)
    package_id = Column(String, ForeignKey("packages.id"), nullable=False, unique=True)

    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    is_hard_constraint = Column(Boolean, default=True)

    # Tracking
    estimated_arrival = Column(DateTime(timezone=True), nullable=True)
    actual_arrival = Column(DateTime(timezone=True), nullable=True)
    was_violated = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return (
            f"<TimeWindow {self.package_id}: {self.window_start} - {self.window_end}>"
        )
