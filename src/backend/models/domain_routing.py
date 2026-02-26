# ==========================================
# FILE: src/backend/models/domain_routing.py
# New domain models for advanced routing
# ==========================================

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Tuple
from datetime import datetime, time, timedelta
from enum import Enum


class TimeWindow(BaseModel):
    """Time window constraint for deliveries"""

    start: datetime
    end: datetime
    is_hard_constraint: bool = True  # True = must deliver in window, False = preference

    @validator("end")
    def end_after_start(cls, v, values):
        if "start" in values and v <= values["start"]:
            raise ValueError("end time must be after start time")
        return v


class VehicleCapacity(BaseModel):
    """Vehicle capacity constraints"""

    max_weight_kg: float = 1000.0
    max_volume_m3: float = 10.0
    max_packages: int = 100
    current_weight_kg: float = 0.0
    current_volume_m3: float = 0.0
    current_packages: int = 0

    def has_capacity_for(self, weight: float, volume: float) -> bool:
        """Check if vehicle can accommodate additional load"""
        return (
            self.current_weight_kg + weight <= self.max_weight_kg
            and self.current_volume_m3 + volume <= self.max_volume_m3
            and self.current_packages + 1 <= self.max_packages
        )

    def add_load(self, weight: float, volume: float):
        """Add load to vehicle"""
        self.current_weight_kg += weight
        self.current_volume_m3 += volume
        self.current_packages += 1

    def remaining_capacity_percent(self) -> float:
        """Calculate remaining capacity percentage (worst case)"""
        weight_pct = (self.max_weight_kg - self.current_weight_kg) / self.max_weight_kg
        volume_pct = (self.max_volume_m3 - self.current_volume_m3) / self.max_volume_m3
        package_pct = (self.max_packages - self.current_packages) / self.max_packages
        return min(weight_pct, volume_pct, package_pct) * 100


class BreakSchedule(BaseModel):
    """Driver break requirements"""

    min_work_hours_before_break: float = 4.0  # Hours before break required
    break_duration_minutes: int = 30
    max_shift_hours: float = 10.0
    breaks_taken: int = 0
    shift_start_time: Optional[datetime] = None
    last_break_time: Optional[datetime] = None

    def needs_break(self, current_time: datetime, hours_worked: float) -> bool:
        """Check if driver needs a break"""
        if not self.shift_start_time:
            return False

        # Check if minimum work hours reached
        if hours_worked >= self.min_work_hours_before_break * (self.breaks_taken + 1):
            return True

        # Check if shift exceeds max hours
        if hours_worked >= self.max_shift_hours:
            return True

        return False

    def schedule_break_time(
        self, current_time: datetime, estimated_hours: float
    ) -> Optional[datetime]:
        """Estimate when next break should be scheduled"""
        if not self.shift_start_time:
            return None

        hours_until_break = (
            self.min_work_hours_before_break * (self.breaks_taken + 1) - estimated_hours
        )
        if hours_until_break <= 0:
            return current_time

        return current_time + timedelta(hours=hours_until_break)


class Depot(BaseModel):
    """Distribution center / depot location"""

    id: str
    name: str
    lat: float
    lon: float
    address: Optional[str] = None
    operating_hours_start: time = time(6, 0)  # 6:00 AM
    operating_hours_end: time = time(22, 0)  # 10:00 PM
    max_vehicles: int = 50
    is_active: bool = True

    def is_open_at(self, check_time: datetime) -> bool:
        """Check if depot is operating at given time"""
        current_time = check_time.time()
        return self.operating_hours_start <= current_time <= self.operating_hours_end


class DeliveryStop(BaseModel):
    """Enhanced delivery stop with all constraints"""

    id: str
    location: "Location"
    package_id: Optional[str] = None
    time_window: Optional[TimeWindow] = None
    service_duration_minutes: int = 5  # Time to complete delivery
    priority: int = 1  # 1=low, 2=medium, 3=high, 4=urgent
    weight_kg: float = 5.0
    volume_m3: float = 0.1
    special_requirements: List[str] = []  # ["signature", "fragile", "cold_chain"]
    customer_notes: Optional[str] = None
    assigned_driver_id: Optional[str] = None
    completed: bool = False
    estimated_arrival: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None


class RouteConstraints(BaseModel):
    """Constraints for route optimization"""

    enforce_time_windows: bool = True
    enforce_capacity: bool = True
    enforce_breaks: bool = True
    allow_split_routes: bool = False  # Allow splitting into multiple routes/drivers
    max_route_duration_hours: float = 10.0
    max_stops_per_route: int = 50
    optimization_objective: str = (
        "minimize_distance"  # minimize_distance, minimize_time, balance_load
    )


class OptimizedRoute(BaseModel):
    """Result of route optimization"""

    driver_id: str
    depot_id: str
    stops: List[DeliveryStop]
    total_distance_km: float
    total_duration_minutes: float
    total_service_time_minutes: float
    break_times: List[datetime] = []
    start_time: datetime
    estimated_end_time: datetime
    capacity_utilization_percent: float
    time_window_violations: int = 0
    route_geometry: Optional[Dict] = None  # GeoJSON route
    stops_count: int = 0

    @validator("stops_count", always=True)
    def set_stops_count(cls, v, values):
        return len(values.get("stops", []))


class MultiDepotRouteRequest(BaseModel):
    """Request for multi-depot route optimization"""

    depots: List[Depot]
    stops: List[DeliveryStop]
    available_drivers: List[Dict]  # driver_id, depot_id, capacity, shift
    constraints: RouteConstraints
    optimization_start_time: datetime = Field(default_factory=datetime.now)


class ReOptimizationTrigger(str, Enum):
    """Reasons for dynamic re-optimization"""

    NEW_JOBS = "new_jobs"
    TRAFFIC_DELAY = "traffic_delay"
    DRIVER_BREAKDOWN = "driver_breakdown"
    TIME_WINDOW_RISK = "time_window_risk"
    MANUAL_REQUEST = "manual_request"


class DynamicReOptimizationRequest(BaseModel):
    """Request for dynamic route re-optimization"""

    route_id: str
    driver_id: str
    current_location: "Location"
    remaining_stop_ids: List[str]
    new_stops: List[DeliveryStop] = []
    trigger: ReOptimizationTrigger
    current_time: datetime = Field(default_factory=datetime.now)
    force_reoptimize: bool = False


# Forward refs
from src.backend.models.domain import Location

DeliveryStop.update_forward_refs()
DynamicReOptimizationRequest.update_forward_refs()
