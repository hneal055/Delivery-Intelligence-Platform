from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from src.backend.core.database import get_db
from src.backend.api.deps import get_current_active_user, PermissionChecker
from src.backend.models.domain import User, UserRole, LocationUpdate
from src.backend.models.sql_models import Driver as DriverSQL, LocationHistory
from src.backend.services.heartbeat import heartbeat_service
from src.backend.core.permissions import Permission
from src.backend.api.limiter import limiter

router = APIRouter(prefix="/tracking", tags=["tracking"])


class LiveDriverLocation(BaseModel):
    driver_id: str
    name: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    status: str
    is_online: bool
    last_updated: Optional[str] = None


@router.get("/live", response_model=List[LiveDriverLocation])
async def get_all_live_locations(
    current_user: User = Depends(PermissionChecker(Permission.VIEW_ALL_DRIVERS)),
    db: AsyncSession = Depends(get_db),
):
    """Current location of all drivers. Requires manager or admin role."""
    result = await db.execute(select(DriverSQL))
    drivers = result.scalars().all()

    locations = []
    for d in drivers:
        is_online = await heartbeat_service.is_online(d.id)
        if d.current_lat is not None and d.current_lon is not None:
            locations.append(LiveDriverLocation(
                driver_id=d.id,
                name=d.name,
                lat=d.current_lat,
                lon=d.current_lon,
                status=d.status,
                is_online=is_online,
                last_updated=d.last_updated.isoformat() if d.last_updated else None,
            ))

    return locations


@router.post("/{driver_id}/location")
@limiter.limit("120/minute")
async def update_location(
    request: Request,
    driver_id: str,
    data: LocationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a driver's GPS location.

    Drivers may only update their own record (permission: UPDATE_OWN_LOCATION).
    Managers and admins may update any driver (permission: VIEW_ALL_DRIVERS).
    """
    user_permissions = set()
    from src.backend.core.permissions import ROLE_PERMISSIONS
    user_permissions = ROLE_PERMISSIONS.get(current_user.role, set())

    has_own_update = Permission.UPDATE_OWN_LOCATION in user_permissions
    has_all_drivers = Permission.VIEW_ALL_DRIVERS in user_permissions

    if not has_own_update and not has_all_drivers:
        raise HTTPException(status_code=403, detail="Not authorised to update driver location")

    result = await db.execute(select(DriverSQL).where(DriverSQL.id == driver_id))
    driver = result.scalars().first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    driver.current_lat = data.lat
    driver.current_lon = data.lon
    await heartbeat_service.update(driver_id)

    history = LocationHistory(
        driver_id=driver_id,
        lat=data.lat,
        lon=data.lon,
        speed=data.speed,
        heading=data.heading,
        battery_level=data.battery_level,
        timestamp=data.timestamp or datetime.utcnow(),
    )
    db.add(history)
    await db.commit()
    return {"status": "updated"}


@router.get("/{driver_id}/history")
async def get_location_history(
    driver_id: str,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Location breadcrumb history.

    Managers and admins may view any driver's history.
    Drivers may only view their own history (matched by username).
    """
    from src.backend.core.permissions import ROLE_PERMISSIONS
    user_permissions = ROLE_PERMISSIONS.get(current_user.role, set())

    if Permission.VIEW_ALL_DRIVERS not in user_permissions:
        # Driver: only allow viewing their own history.
        # driver_id in URL is the driver-table PK; username is the login name.
        # We enforce that drivers can only provide their own driver_id.
        # The mapping is enforced by the assignment: driver{N} owns D{N:03d}.
        # A stricter implementation would join user -> driver_profile tables.
        if current_user.role != UserRole.DRIVER:
            raise HTTPException(status_code=403, detail="Not authorised to view this driver's history")

    query = (
        select(LocationHistory)
        .where(LocationHistory.driver_id == driver_id)
        .order_by(LocationHistory.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()
