from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.backend.core.database import get_db
from src.backend.api.deps import get_current_active_user
from src.backend.models.sql_models_routing import (
    TimeWindowConstraint,
    VehicleProfile,
    RouteHistory,
)

router = APIRouter(
    prefix="/advanced-route",
    tags=["advanced-routing"],
    dependencies=[Depends(get_current_active_user)],
)


# --- Request / Response Models ---

class TimeWindowRequest(BaseModel):
    package_id: str
    window_start: datetime
    window_end: datetime
    is_hard_constraint: bool = True


class TimeWindowResponse(BaseModel):
    id: str
    package_id: str
    window_start: datetime
    window_end: datetime
    is_hard_constraint: bool
    was_violated: bool
    created_at: Optional[datetime] = None


class VehicleProfileRequest(BaseModel):
    vehicle_id: str
    max_weight_kg: float = 1000.0
    max_volume_m3: float = 10.0
    max_packages: int = 100
    vehicle_type: str = "van"
    fuel_type: str = "gasoline"
    avg_speed_kmh: float = 45.0
    has_refrigeration: bool = False
    has_lift_gate: bool = False
    special_capabilities: Optional[List[str]] = None


class OptimizeSingleRequest(BaseModel):
    driver_id: str
    depot_id: str
    package_ids: List[str]
    constraints: dict
    start_time: datetime


class OptimizeMultiDepotRequest(BaseModel):
    depots: List[dict]
    stops: List[dict]
    available_drivers: List[str]
    constraints: dict
    optimization_start_time: datetime


# --- Endpoints ---

@router.get("/health")
async def health_check():
    """Health check for advanced routing service."""
    return {"status": "ok", "version": "1.0"}


@router.post("/time-windows", response_model=TimeWindowResponse, status_code=status.HTTP_200_OK)
async def create_time_window(
    payload: TimeWindowRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create or update a delivery time window constraint for a package."""
    if payload.window_end <= payload.window_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="window_end must be after window_start",
        )

    result = await db.execute(
        select(TimeWindowConstraint).where(
            TimeWindowConstraint.package_id == payload.package_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.window_start = payload.window_start
        existing.window_end = payload.window_end
        existing.is_hard_constraint = payload.is_hard_constraint
        await db.commit()
        await db.refresh(existing)
        record = existing
    else:
        record = TimeWindowConstraint(
            package_id=payload.package_id,
            window_start=payload.window_start,
            window_end=payload.window_end,
            is_hard_constraint=payload.is_hard_constraint,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

    return TimeWindowResponse(
        id=record.id,
        package_id=record.package_id,
        window_start=record.window_start,
        window_end=record.window_end,
        is_hard_constraint=record.is_hard_constraint,
        was_violated=record.was_violated,
        created_at=record.created_at,
    )


@router.post("/vehicles/profile")
async def create_vehicle_profile(
    payload: VehicleProfileRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create or update a vehicle capacity profile."""
    result = await db.execute(
        select(VehicleProfile).where(VehicleProfile.vehicle_id == payload.vehicle_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        for field, value in payload.model_dump().items():
            setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        return {"message": "Vehicle profile updated", "vehicle_id": existing.vehicle_id}

    profile = VehicleProfile(**payload.model_dump())
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return {"message": "Vehicle profile created", "vehicle_id": profile.vehicle_id}


@router.post("/optimize-single")
async def optimize_single_route(payload: OptimizeSingleRequest):
    """Optimize a single driver's route (stub — optimization engine placeholder)."""
    return {
        "message": f"Route optimized with {len(payload.package_ids)} stops",
        "route_id": f"route-{payload.driver_id}-{int(datetime.now(timezone.utc).timestamp())}",
        "driver_id": payload.driver_id,
        "depot_id": payload.depot_id,
        "stops_count": len(payload.package_ids),
        "start_time": payload.start_time.isoformat(),
    }


@router.post("/optimize-multi-depot")
async def optimize_multi_depot_route(payload: OptimizeMultiDepotRequest):
    """Optimize routes across multiple depots (stub — optimization engine placeholder)."""
    return {
        "message": f"Multi-depot optimization complete: {len(payload.stops)} stops across {len(payload.depots)} depots",
        "route_id": f"multi-{int(datetime.now(timezone.utc).timestamp())}",
        "depots_count": len(payload.depots),
        "stops_count": len(payload.stops),
        "drivers_count": len(payload.available_drivers),
    }


@router.get("/analytics/capacity-utilization")
async def get_capacity_utilization(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
):
    """Capacity utilization across recent optimized routes."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(RouteHistory).where(RouteHistory.created_at >= cutoff)
    )
    routes = result.scalars().all()

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
        "average_utilization_percent": round(sum(utilizations) / len(utilizations), 2),
        "min_utilization_percent": round(min(utilizations), 2),
        "max_utilization_percent": round(max(utilizations), 2),
        "total_routes_optimized": len(routes),
    }


@router.get("/analytics/capacity-utilization-summary")
async def get_capacity_utilization_summary(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
):
    """Summary stats for capacity utilization."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(RouteHistory).where(RouteHistory.created_at >= cutoff)
    )
    routes = result.scalars().all()

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
        "average_utilization_percent": round(sum(utilizations) / len(utilizations), 2),
        "min_utilization_percent": round(min(utilizations), 2),
        "max_utilization_percent": round(max(utilizations), 2),
        "total_routes_optimized": len(routes),
    }


@router.get("/analytics/time-window-compliance")
async def get_time_window_compliance(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
):
    """Time window compliance rate across recent routes."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(RouteHistory).where(RouteHistory.created_at >= cutoff)
    )
    routes = result.scalars().all()

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
