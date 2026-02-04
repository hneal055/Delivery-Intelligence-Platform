from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from src.backend.models.domain import Location, Driver
from src.analytics.geofencing.engine import geofence_engine
from src.analytics.image_analysis.verifier import image_verifier
from src.backend.services.auth import get_current_device
from src.backend.services.notifications import notification_service, NotificationEvent

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

@router.post("/confirm")
async def confirm_delivery(
    package_id: str,
    driver_id: str,
    background_tasks: BackgroundTasks,
    photo: UploadFile = File(...),
    authorized: bool = Depends(get_current_device)
):
    """
    Finalizes a delivery by uploading a Proof-of-Delivery (PoD) photo.
    The photo is analyzed by the AI Stub to ensure quality.
    """
    # 1. Read the uploaded file bytes
    content = await photo.read()
    
    # 2. Verify image quality with AI Stub
    result = image_verifier.verify_delivery_photo(content)
    
    if not result.is_valid:
        return {
            "status": "failed",
            "reason": "Image validation rejected",
            "details": result.issues
        }
        
    # 3. (Mock) Save success state
    # In a real app, we would write to database and S3 here.

    # 4. Trigger Async Notification
    background_tasks.add_task(
        notification_service.send_notification,
        recipient_id='customer_mock',
        contact_info='customer@example.com',
        event=NotificationEvent.DELIVERED,
        message=f'Your package {package_id} has been delivered by {driver_id}.'
    )
    
    return {
        "status": "confirmed",
        "package_id": package_id,
        "verification_score": result.confidence_score,
        "ai_detection": result.detected_objects,
        "message": "Delivery confirmed successfully. Great job!"
    }
