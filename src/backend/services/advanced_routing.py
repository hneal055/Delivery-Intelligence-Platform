# ==========================================
# FILE: src/backend/services/advanced_routing.py
# Advanced routing optimization service
# ==========================================

from typing import List, Optional, Dict
from datetime import datetime, timedelta
import math
from sqlalchemy.orm import Session

from src.backend.models.sql_models_routing import (
    Depot as SQLDepot,
    VehicleProfile as SQLVehicleProfile,
    RouteHistory,
    TimeWindowConstraint,
    DriverBreakLog,
)


class AdvancedRoutingService:
    """Service for advanced route optimization with constraints"""

    def __init__(self, db: Session):
        self.db = db

    def create_depot(
        self,
        name: str,
        lat: float,
        lon: float,
        address: Optional[str] = None,
        operating_hours_start: Optional[str] = "06:00:00",
        operating_hours_end: Optional[str] = "22:00:00",
        max_vehicles: int = 50,
    ) -> SQLDepot:
        """Create a new depot"""
        from datetime import time

        depot = SQLDepot(
            name=name,
            lat=lat,
            lon=lon,
            address=address,
            operating_hours_start=time.fromisoformat(operating_hours_start),
            operating_hours_end=time.fromisoformat(operating_hours_end),
            max_vehicles=max_vehicles,
            is_active=True,
        )
        self.db.add(depot)
        self.db.commit()
        self.db.refresh(depot)
        return depot

    def get_depots(self, active_only: bool = True) -> List[SQLDepot]:
        """Get all depots"""
        query = self.db.query(SQLDepot)
        if active_only:
            query = query.filter(SQLDepot.is_active == True)
        return query.all()

    def create_vehicle_profile(
        self,
        vehicle_id: str,
        max_weight_kg: float = 1000.0,
        max_volume_m3: float = 10.0,
        max_packages: int = 100,
        vehicle_type: str = "van",
        fuel_type: str = "gasoline",
        avg_speed_kmh: float = 45.0,
        has_refrigeration: bool = False,
        has_lift_gate: bool = False,
        special_capabilities: Optional[List[str]] = None,
    ) -> SQLVehicleProfile:
        """Create or update vehicle profile"""
        existing = (
            self.db.query(SQLVehicleProfile)
            .filter(SQLVehicleProfile.vehicle_id == vehicle_id)
            .first()
        )

        if existing:
            existing.max_weight_kg = max_weight_kg
            existing.max_volume_m3 = max_volume_m3
            existing.max_packages = max_packages
            existing.vehicle_type = vehicle_type
            existing.fuel_type = fuel_type
            existing.avg_speed_kmh = avg_speed_kmh
            existing.has_refrigeration = has_refrigeration
            existing.has_lift_gate = has_lift_gate
            existing.special_capabilities = special_capabilities
            self.db.commit()
            self.db.refresh(existing)
            return existing

        profile = SQLVehicleProfile(
            vehicle_id=vehicle_id,
            max_weight_kg=max_weight_kg,
            max_volume_m3=max_volume_m3,
            max_packages=max_packages,
            vehicle_type=vehicle_type,
            fuel_type=fuel_type,
            avg_speed_kmh=avg_speed_kmh,
            has_refrigeration=has_refrigeration,
            has_lift_gate=has_lift_gate,
            special_capabilities=special_capabilities,
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def create_time_window(
        self,
        package_id: str,
        window_start: datetime,
        window_end: datetime,
        is_hard_constraint: bool = True,
    ) -> TimeWindowConstraint:
        """Create time window constraint for a package"""
        existing = (
            self.db.query(TimeWindowConstraint)
            .filter(TimeWindowConstraint.package_id == package_id)
            .first()
        )

        if existing:
            existing.window_start = window_start
            existing.window_end = window_end
            existing.is_hard_constraint = is_hard_constraint
            self.db.commit()
            self.db.refresh(existing)
            return existing

        constraint = TimeWindowConstraint(
            package_id=package_id,
            window_start=window_start,
            window_end=window_end,
            is_hard_constraint=is_hard_constraint,
        )
        self.db.add(constraint)
        self.db.commit()
        self.db.refresh(constraint)
        return constraint

    def get_route_history(self, driver_id: str, limit: int = 10) -> List[RouteHistory]:
        """Get route optimization history for a driver"""
        return (
            self.db.query(RouteHistory)
            .filter(RouteHistory.driver_id == driver_id)
            .order_by(RouteHistory.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_capacity_utilization_analytics(self, days: int = 7) -> Dict:
        """Get capacity utilization statistics"""
        cutoff_date = datetime.now() - timedelta(days=days)
        routes = (
            self.db.query(RouteHistory)
            .filter(RouteHistory.created_at >= cutoff_date)
            .all()
        )

        if not routes:
            return {
                "period_days": days,
                "average_utilization_percent": 0.0,
                "min_utilization_percent": 0.0,
                "max_utilization_percent": 0.0,
                "total_routes_optimized": 0,
            }

        utilizations = [r.capacity_utilization_percent for r in routes]
        return {
            "period_days": days,
            "average_utilization_percent": round(
                sum(utilizations) / len(utilizations), 2
            ),
            "min_utilization_percent": round(min(utilizations), 2),
            "max_utilization_percent": round(max(utilizations), 2),
            "total_routes_optimized": len(routes),
        }

    def get_time_window_compliance_analytics(self, days: int = 7) -> Dict:
        """Get time window compliance statistics"""
        cutoff_date = datetime.now() - timedelta(days=days)
        routes = (
            self.db.query(RouteHistory)
            .filter(RouteHistory.created_at >= cutoff_date)
            .all()
        )

        if not routes:
            return {
                "period_days": days,
                "total_violations": 0,
                "total_routes": 0,
                "compliance_rate_percent": 100.0,
            }

        total_violations = sum(r.time_window_violations for r in routes)
        total_routes = len(routes)
        compliance_rate = (
            ((total_routes - total_violations) / total_routes * 100)
            if total_routes > 0
            else 100.0
        )

        return {
            "period_days": days,
            "total_violations": total_violations,
            "total_routes": total_routes,
            "compliance_rate_percent": round(compliance_rate, 2),
        }
