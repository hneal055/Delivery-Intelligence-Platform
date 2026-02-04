from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.backend.models.domain import Location, Driver
from src.analytics.geofencing.engine import geofence_engine
from src.backend.services.auth import get_current_device

router = APIRouter(prefix="/delivery", tags=["delivery"])

# Schema for the request body
class LocationVerifyRequest(BaseModel):
    driver_id: str
    current_location: Location
    target_delivery_location: Location

@router.post("/verify-location")
async def verify_location(
    request: LocationVerifyRequest,
    authorized: bool = Depends(get_current_device)
):
    """
    Checks if the driver is close enough to the delivery target.
    Logic: Uses the GeofenceEngine to calculate proximity.
    """
    
    # 1. Calculate distance using the Engine
    dist_meters = geofence_engine.calculate_distance_meters(
        request.current_location, 
        request.target_delivery_location
    )
    
    # 2. Define the rule (e.g., must be within 50 meters)
    MAX_DISTANCE_METERS = 50.0
    
    if dist_meters > MAX_DISTANCE_METERS:
        # LOGIC REJECTED
        return {
            "allowed": False, 
            "status": "rejected",
            "message": f"You are {dist_meters}m away. Please move closer (Limit: {MAX_DISTANCE_METERS}m)."
        }
    
    # LOGIC ACCEPTED
    return {
        "allowed": True, 
        "status": "approved",
        "message": "Perfect match. You are at the delivery location."
    }
