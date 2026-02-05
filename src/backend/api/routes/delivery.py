from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    Request,
)
from pydantic import BaseModel
import time
from src.backend.models.domain import Location, Driver, User
from src.analytics.geofencing.engine import geofence_engine
from src.analytics.image_analysis.verifier import image_verifier
from src.backend.api.deps import get_current_active_user
from src.backend.services.notifications import notification_service, NotificationEvent
from src.backend.api.limiter import limiter
from src.backend.api.metrics import driver_heartbeats

router = APIRouter(prefix="/delivery", tags=["delivery"])


# Schema for the request body
# Add driver_id (optional for backward compat, but used for metrics)
class LocationVerifyRequest(BaseModel):
    driver_id: str = "unknown"
    current_location: Location
    target_delivery_location: Location


@router.post("/verify-location")
@limiter.limit("120/minute")
async def verify_location(
    request: Request,
    payload: LocationVerifyRequest,
    current_user: User = Depends(get_current_active_user)
):
    # Update heartbeat
    # Use driver_id from payload if present, else username
    driver_id = payload.driver_id if payload.driver_id != "unknown" else current_user.username
    driver_heartbeats[driver_id] = time.time()

    # Verify if the driver is within valid range of the delivery target
    is_valid, distance = geofence_engine.verify_delivery_location(
        (payload.current_location.lat, payload.current_location.lon),
        (payload.target_delivery_location.lat, payload.target_delivery_location.lon),
    )

    if is_valid:
        return {"message": "Location Verified", "allowed": True, "distance": distance}
    else:
        return {
            "message": f"Driver is too far ({distance:.2f}m) from delivery point",
            "allowed": False,
            "distance": distance,
        }

@router.post("/confirm")
async def confirm_delivery(
    package_id: str = Form(...),
    driver_id: str = Form(...),
    photo: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_active_user)
):
    # Update Heartbeat
    driver_heartbeats[driver_id] = time.time()

    # 1. Read file content
    content = await photo.read()
    
    # 2. Verify Image (Blur/Darkness)
    is_valid_image, reason = image_verifier.verify_proof_of_delivery(content)
    
    if not is_valid_image:
         raise HTTPException(status_code=400, detail=f"Invalid Proof of Delivery: {reason}")
    
    # 3. (Mock) Save to Object Store / Database
    # save_to_s3(content, filename)
    
    # 4. Trigger Async Notification
    background_tasks.add_task(
        notification_service.send_notification,
        "customer_placeholder",
        "email@example.com",
        NotificationEvent.DELIVERY_COMPLETED,
        f"Package {package_id} delivered by {driver_id}"
    )

    return {"status": "success", "package_id": package_id, "verification": "passed"}
