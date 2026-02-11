from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from src.backend.core.database import get_db
from src.backend.api.deps import get_current_active_user
from src.backend.models.domain import User
from src.backend.models.sql_models import Driver as DriverSQL, Package as PackageSQL
from src.backend.services.heartbeat import heartbeat_service

router = APIRouter(prefix="/dispatch", tags=["dispatch"])


class DriverResponse(BaseModel):
    id: str
    name: str
    status: str
    current_lat: Optional[float] = None
    current_lon: Optional[float] = None
    last_updated: Optional[str] = None
    package_count: int = 0
    is_online: bool = False


class PackageResponse(BaseModel):
    id: str
    driver_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    dest_lat: float
    dest_lon: float
    dest_address: Optional[str] = None
    status: str
    section: Optional[str] = None
    distance_km: Optional[float] = None
    predicted_eta_seconds: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DashboardSummary(BaseModel):
    total_drivers: int
    active_drivers: int
    online_drivers: int
    total_packages: int
    pending_packages: int
    delivered_packages: int
    exception_packages: int


@router.get("/drivers", response_model=List[DriverResponse])
async def list_drivers(
    status: Optional[str] = Query(None, description="Filter by driver status"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all drivers with their current status, location, and package count."""
    query = select(DriverSQL)
    if status:
        query = query.where(DriverSQL.status == status)

    result = await db.execute(query)
    drivers = result.scalars().all()

    responses = []
    for d in drivers:
        # Count packages assigned to this driver
        pkg_count_result = await db.execute(
            select(func.count()).select_from(PackageSQL).where(PackageSQL.driver_id == d.id)
        )
        pkg_count = pkg_count_result.scalar() or 0

        is_online = await heartbeat_service.is_online(d.id)

        responses.append(DriverResponse(
            id=d.id,
            name=d.name,
            status=d.status,
            current_lat=d.current_lat,
            current_lon=d.current_lon,
            last_updated=d.last_updated.isoformat() if d.last_updated else None,
            package_count=pkg_count,
            is_online=is_online,
        ))

    return responses


@router.get("/drivers/{driver_id}/packages", response_model=List[PackageResponse])
async def get_driver_packages(
    driver_id: str,
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all packages assigned to a specific driver."""
    query = select(PackageSQL).where(PackageSQL.driver_id == driver_id)
    if status:
        query = query.where(PackageSQL.status == status)

    result = await db.execute(query)
    packages = result.scalars().all()

    return [
        PackageResponse(
            id=p.id,
            driver_id=p.driver_id,
            vehicle_id=p.vehicle_id,
            dest_lat=p.dest_lat,
            dest_lon=p.dest_lon,
            dest_address=p.dest_address,
            status=p.status,
            section=p.section,
            distance_km=p.distance_km,
            predicted_eta_seconds=p.predicted_eta_seconds,
            created_at=p.created_at.isoformat() if p.created_at else None,
            updated_at=p.updated_at.isoformat() if p.updated_at else None,
        )
        for p in packages
    ]


@router.get("/packages", response_model=List[PackageResponse])
async def list_packages(
    status: Optional[str] = Query(None, description="Filter by package status"),
    driver_id: Optional[str] = Query(None, description="Filter by assigned driver"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all packages with optional filters."""
    query = select(PackageSQL)
    if status:
        query = query.where(PackageSQL.status == status)
    if driver_id:
        query = query.where(PackageSQL.driver_id == driver_id)

    result = await db.execute(query)
    packages = result.scalars().all()

    return [
        PackageResponse(
            id=p.id,
            driver_id=p.driver_id,
            vehicle_id=p.vehicle_id,
            dest_lat=p.dest_lat,
            dest_lon=p.dest_lon,
            dest_address=p.dest_address,
            status=p.status,
            section=p.section,
            distance_km=p.distance_km,
            predicted_eta_seconds=p.predicted_eta_seconds,
            created_at=p.created_at.isoformat() if p.created_at else None,
            updated_at=p.updated_at.isoformat() if p.updated_at else None,
        )
        for p in packages
    ]


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get dispatch dashboard summary statistics."""
    # Driver counts
    total_drivers_result = await db.execute(select(func.count()).select_from(DriverSQL))
    total_drivers = total_drivers_result.scalar() or 0

    active_drivers_result = await db.execute(
        select(func.count()).select_from(DriverSQL).where(DriverSQL.status == "active")
    )
    active_drivers = active_drivers_result.scalar() or 0

    online_drivers = await heartbeat_service.get_online_count()

    # Package counts
    total_packages_result = await db.execute(select(func.count()).select_from(PackageSQL))
    total_packages = total_packages_result.scalar() or 0

    pending_result = await db.execute(
        select(func.count()).select_from(PackageSQL).where(PackageSQL.status == "pending")
    )
    pending_packages = pending_result.scalar() or 0

    delivered_result = await db.execute(
        select(func.count()).select_from(PackageSQL).where(PackageSQL.status == "delivered")
    )
    delivered_packages = delivered_result.scalar() or 0

    exception_result = await db.execute(
        select(func.count()).select_from(PackageSQL).where(PackageSQL.status == "exception")
    )
    exception_packages = exception_result.scalar() or 0

    return DashboardSummary(
        total_drivers=total_drivers,
        active_drivers=active_drivers,
        online_drivers=online_drivers,
        total_packages=total_packages,
        pending_packages=pending_packages,
        delivered_packages=delivered_packages,
        exception_packages=exception_packages,
    )


# --- Phase 2: Dispatch & Scheduling Endpoints ---

from fastapi import HTTPException
from src.backend.services.dispatch_service import DispatchService
from src.backend.models.domain import DispatchJob, DispatchJobCreate, AvailabilityCreate

@router.post("/jobs", response_model=DispatchJob)
async def create_job(
    job_data: DispatchJobCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new dispatch job."""
    service = DispatchService(db)
    return await service.create_job(job_data)

@router.get("/jobs", response_model=List[DispatchJob])
async def list_jobs(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all dispatch jobs, optionally filtered by status."""
    service = DispatchService(db)
    return await service.get_all_jobs(status)

@router.put("/jobs/{job_id}/assign")
async def assign_job(
    job_id: str,
    driver_id: str = Query(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign a driver to a job."""
    service = DispatchService(db)
    try:
        job = await service.assign_driver(job_id, driver_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/availability")
async def set_availability(
    data: AvailabilityCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Set availability for a driver."""
    service = DispatchService(db)
    await service.set_availability(data.driver_id, data.date, data.is_available, data.start_time, data.end_time)
    return {"message": "Availability updated"}


@router.get("/jobs/{job_id}", response_model=DispatchJob)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific dispatch job."""
    service = DispatchService(db)
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
