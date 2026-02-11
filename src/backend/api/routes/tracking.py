from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from src.backend.core.database import get_db
from src.backend.api.deps import get_current_active_user
from src.backend.models.domain import User, LocationUpdate
from src.backend.models.sql_models import Driver as DriverSQL, LocationHistory
from src.backend.services.heartbeat import heartbeat_service

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
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current location of all drivers. Used for initial map load before WebSocket takes over."""
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
async def update_location(
    driver_id: str,
    data: LocationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update driver location and record in history."""
    result = await db.execute(select(DriverSQL).where(DriverSQL.id == driver_id))
    driver = result.scalars().first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    driver.current_lat = data.lat
    driver.current_lon = data.lon
    await heartbeat_service.update(driver_id)

    # Add to History
    history = LocationHistory(
        driver_id=driver_id,
        lat=data.lat,
        lon=data.lon,
        speed=data.speed,
        heading=data.heading,
        battery_level=data.battery_level,
        timestamp=data.timestamp or datetime.utcnow()
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
    """Get location history for breadcrumbs."""
    query = select(LocationHistory).where(LocationHistory.driver_id == driver_id).order_by(LocationHistory.timestamp.desc()).limit(limit)
    result = await db.execute(query)
    history = result.scalars().all()
    return history
