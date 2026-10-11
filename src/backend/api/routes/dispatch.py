import secrets
import uuid

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
from src.backend.api.deps import PermissionChecker

from src.backend.core.database import get_db

from src.backend.models.domain import User, UserRole, DispatchJob, DispatchJobCreate, AvailabilityCreate, JobStatus
from src.backend.models.sql_models import (
    Driver as DriverSQL,
    Package as PackageSQL,
    DispatchJob as DispatchJobSQL,
    DriverAvailability,
)
from src.backend.services.heartbeat import heartbeat_service
from src.backend.services.geocoding import geocode_address
from src.backend.core.permissions import Permission


from src.backend.api.limiter import limiter

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
    current_user: User = Depends(PermissionChecker(Permission.VIEW_ALL_DRIVERS)),
    db: AsyncSession = Depends(get_db),
):
    """List all drivers. Requires manager or admin role."""
    query = select(DriverSQL)
    if status:
        query = query.where(DriverSQL.status == status)

    result = await db.execute(query)
    drivers = result.scalars().all()

    responses = []
    for d in drivers:
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
    current_user: User = Depends(PermissionChecker(Permission.VIEW_ALL_PACKAGES)),
    db: AsyncSession = Depends(get_db),
):
    """List packages for a specific driver. Requires manager or admin role."""
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


@router.get("/deliveries", response_model=List[PackageResponse])
async def list_deliveries(
    status: Optional[str] = Query(None, description="Filter by package status"),
    driver_id: Optional[str] = Query(None, description="Filter by assigned driver"),
    limit: int = Query(200, ge=1, le=1000, description="Max results to return"),
    current_user: User = Depends(PermissionChecker(Permission.VIEW_ASSIGNED_PACKAGES)),
    db: AsyncSession = Depends(get_db),
):
    """Mobile-friendly package list. Drivers see only their assigned packages."""
    # A driver's ID is their login username (see drivers table).
    if current_user.role == UserRole.DRIVER:
        driver_id = current_user.username
        # The app refreshes this list while open, so it doubles as "online".
        await heartbeat_service.update(driver_id)
    query = select(PackageSQL)
    if status:
        query = query.where(PackageSQL.status == status)
    if driver_id:
        query = query.where(PackageSQL.driver_id == driver_id)
    query = query.limit(limit)

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
    limit: int = Query(200, ge=1, le=1000, description="Max results to return"),
    current_user: User = Depends(PermissionChecker(Permission.VIEW_ALL_PACKAGES)),
    db: AsyncSession = Depends(get_db),
):
    """List all packages (dispatcher view). Requires manager or admin role."""
    query = select(PackageSQL)
    if status:
        query = query.where(PackageSQL.status == status)
    if driver_id:
        query = query.where(PackageSQL.driver_id == driver_id)
    query = query.limit(limit)

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
    current_user: User = Depends(PermissionChecker(Permission.VIEW_ANALYTICS)),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard statistics. Requires manager or admin role."""
    total_drivers_result = await db.execute(select(func.count()).select_from(DriverSQL))
    total_drivers = total_drivers_result.scalar() or 0

    active_drivers_result = await db.execute(
        select(func.count()).select_from(DriverSQL).where(DriverSQL.status == "active")
    )
    active_drivers = active_drivers_result.scalar() or 0
    online_drivers = await heartbeat_service.get_online_count()

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


@router.post("/jobs", response_model=DispatchJob)
@limiter.limit("60/minute")
async def create_job(
    request: Request,
    job_data: DispatchJobCreate,
    current_user: User = Depends(PermissionChecker(Permission.MANAGE_JOBS)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new dispatch job. Requires manager or admin role.

    With dest_address (and no package_id) the address is geocoded and a new
    package is created for the job. If a driver is given, the job's package
    is assigned to them so it appears on their manifest.
    """
    if job_data.driver_id and await db.get(DriverSQL, job_data.driver_id) is None:
        raise HTTPException(status_code=404, detail="Driver not found")

    package = None
    if job_data.package_id:
        package = await db.get(PackageSQL, job_data.package_id)
        if package is None:
            raise HTTPException(status_code=404, detail="Package not found")
    elif job_data.dest_address and job_data.dest_address.strip():
        location = await geocode_address(job_data.dest_address.strip())
        if location is None:
            raise HTTPException(
                status_code=422,
                detail="Address not found. Check the street, city and state.",
            )
        package = PackageSQL(
            id=str(uuid.uuid4()),
            dest_lat=location.lat,
            dest_lon=location.lon,
            dest_address=location.matched_address,
            status="pending",
            priority=job_data.priority,
            tracking_code=_new_tracking_code(),
        )
        db.add(package)
        # Insert the package before the job that references it; there is no
        # ORM relationship to make SQLAlchemy order these for us.
        await db.flush()

    job = DispatchJobSQL(
        driver_id=job_data.driver_id,
        title=job_data.title,
        type=job_data.type.value if hasattr(job_data.type, "value") else job_data.type,
        priority=job_data.priority,
        notes=job_data.notes,
        scheduled_at=job_data.scheduled_at,
        package_id=package.id if package else None,
        status="assigned" if job_data.driver_id else "pending",
    )
    if package and job_data.driver_id:
        package.driver_id = job_data.driver_id
        if package.status == "pending":
            package.status = "assigned"

    db.add(job)
    await db.commit()
    await db.refresh(job)

    return job


def _new_tracking_code() -> str:
    """Short code for labels and barcodes, e.g. CCC-7K3QX9M2."""
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I/L
    return "CCC-" + "".join(secrets.choice(alphabet) for _ in range(8))


@router.get("/jobs", response_model=List[DispatchJob])
async def list_jobs(
    status: Optional[str] = None,
    current_user: User = Depends(PermissionChecker(Permission.MANAGE_JOBS)),
    db: AsyncSession = Depends(get_db),
):
    """List dispatch jobs. Requires manager or admin role."""
    query = select(DispatchJobSQL)

    if status:
        query = query.where(
            DispatchJobSQL.status == status
        )

    result = await db.execute(query)

    return result.scalars().all()


@router.put("/jobs/{job_id}/assign")
@limiter.limit("60/minute")
async def assign_job(
    request: Request,
    job_id: str,
    driver_id: str = Query(...),
    current_user: User = Depends(PermissionChecker(Permission.MANAGE_JOBS)),
    db: AsyncSession = Depends(get_db),
):
    """Assign a driver to a job. Requires manager or admin role."""
    job_result = await db.execute(
        select(DispatchJobSQL).where(
            DispatchJobSQL.id == job_id
        )
    )

    job = job_result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    driver_result = await db.execute(
        select(DriverSQL).where(
            DriverSQL.id == driver_id
        )
    )

    driver = driver_result.scalar_one_or_none()

    if not driver:
        raise HTTPException(
            status_code=404,
            detail="Driver not found"
        )

    job.driver_id = driver_id
    job.status = "assigned"

    # The package goes with the job, so it shows on the driver's manifest.
    if job.package_id:
        package = await db.get(PackageSQL, job.package_id)
        if package:
            package.driver_id = driver_id
            if package.status == "pending":
                package.status = "assigned"

    await db.commit()
    await db.refresh(job)

    return job


@router.post("/availability")
@limiter.limit("60/minute")
async def set_availability(
    request: Request,
    data: AvailabilityCreate,
    current_user: User = Depends(PermissionChecker(Permission.MANAGE_JOBS)),
    db: AsyncSession = Depends(get_db),
):
    """Set driver availability. Requires manager or admin role."""
    availability = DriverAvailability(
        driver_id=data.driver_id,
        date=data.date,
        is_available=data.is_available,
        start_time=data.start_time,
        end_time=data.end_time,
    )

    db.add(availability)

    await db.commit()
    await db.refresh(availability)

    return _availability_dict(availability)


def _availability_dict(a: DriverAvailability) -> dict:
    return {
        "id": a.id,
        "driver_id": a.driver_id,
        "date": a.date.isoformat() if a.date else None,
        "is_available": a.is_available,
        "start_time": a.start_time,
        "end_time": a.end_time,
    }


@router.get("/availability")
async def list_availability(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    driver_id: Optional[str] = Query(None),
    current_user: User = Depends(PermissionChecker(Permission.MANAGE_JOBS)),
    db: AsyncSession = Depends(get_db),
):
    """Driver availability between two dates. Requires manager or admin role."""
    query = select(DriverAvailability).where(
        DriverAvailability.date >= start_date,
        DriverAvailability.date <= end_date,
    )
    if driver_id:
        query = query.where(DriverAvailability.driver_id == driver_id)
    result = await db.execute(query.order_by(DriverAvailability.date))
    return [_availability_dict(a) for a in result.scalars().all()]



@router.get("/jobs/{job_id}", response_model=DispatchJob)
async def get_job(
    job_id: str,
    current_user: User = Depends(PermissionChecker(Permission.MANAGE_JOBS)),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific dispatch job. Requires manager or admin role."""

    result = await db.execute(
        select(DispatchJobSQL).where(
            DispatchJobSQL.id == job_id
        )
    )

    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    return job


@router.put("/jobs/{job_id}/status", response_model=DispatchJob)
async def update_job_status(
    job_id: str,
    status: JobStatus = Query(...),
    current_user: User = Depends(PermissionChecker(Permission.MANAGE_JOBS)),
    db: AsyncSession = Depends(get_db),
):
    """Set a job's status. Requires manager or admin role."""
    job = await db.get(DispatchJobSQL, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = status.value
    job.completed_at = datetime.now(timezone.utc) if status == JobStatus.COMPLETED else None
    await db.commit()
    await db.refresh(job)
    return job


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(
    job_id: str,
    current_user: User = Depends(PermissionChecker(Permission.MANAGE_JOBS)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a job. Completed jobs are part of the delivery record and are
    kept; cancel a job instead if it should not be done. Requires manager or
    admin role."""
    job = await db.get(DispatchJobSQL, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status == JobStatus.COMPLETED.value:
        raise HTTPException(status_code=409, detail="Completed jobs cannot be deleted")

    await db.delete(job)
    await db.commit()
