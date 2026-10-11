import logging
import math
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/geofence")

class GeofenceCheckRequest(BaseModel):
    driver_id: str
    latitude: float
    longitude: float
    target_latitude: float
    target_longitude: float
    radius_meters: float = 100.0

@router.post("/verify")
async def verify_geofence(payload: GeofenceCheckRequest):
    """Verify if a driver's current coordinates are within the target geofence radius."""
    try:
        lat1, lon1 = math.radians(payload.latitude), math.radians(payload.longitude)
        lat2, lon2 = math.radians(payload.target_latitude), math.radians(payload.target_longitude)
        
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.asin(math.sqrt(a))
        earth_radius_meters = 6371000
        distance = c * earth_radius_meters
        
        is_inside = distance <= payload.radius_meters
        
        logger.info(f"Geofence check for driver {payload.driver_id}: distance={distance:.2f}m, inside={is_inside}")
        
        return {
            "driver_id": payload.driver_id,
            "distance_meters": round(distance, 2),
            "radius_meters": payload.radius_meters,
            "is_inside": is_inside,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error processing geofence verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))