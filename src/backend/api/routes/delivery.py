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
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.models.domain import Location, Driver, User
from src.analytics.geofencing.engine import geofence_engine
from src.analytics.image_analysis.verifier import image_verifier
from src.backend.api.deps import get_current_active_user
from src.backend.services.notifications import notification_service, NotificationEvent
from src.backend.services import delivery_service
from src.backend.api.limiter import limiter
from src.backend.api.metrics import driver_heartbeats, DELIVERIES_COMPLETED
from src.backend.core.database import get_db

router = APIRouter(prefix="/delivery", tags=["delivery"])


# Schema for the request body
# Add driver_id (optional for backward compat, but used for metrics)
class LocationVerifyRequest(BaseModel):
    driver_id: str = "unknown"
    current_location: Location
    target_delivery_location: Location


@router.post("/verify-location")
@limiter.limit("1000/minute") # Increased for simulation
async def verify_location(
    request: Request,
    payload: LocationVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Update heartbeat
    # Use driver_id from payload if present, else username
    driver_id = payload.driver_id if payload.driver_id != "unknown" else current_user.username
    driver_heartbeats[driver_id] = time.time()
    
    # Save location to Database
    await delivery_service.update_driver_location(
        db, 
        driver_id, 
        payload.current_location.lat, 
        payload.current_location.lon
    )

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
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Update Heartbeat
    driver_heartbeats[driver_id] = time.time()

    # 1. Read file content
    content = await photo.read()
    
    # 1.5 Save Proof of Delivery (Storage)
    import os
    # Move up from api/routes to backend root
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    upload_dir = os.path.join(base_dir, "uploads", "proofs")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, f"{package_id}_{driver_id}.jpg")
    with open(file_path, "wb") as f:
        f.write(content)

    # 2. Verify Image (Blur/Darkness)
    is_valid_image, reason = image_verifier.verify_proof_of_delivery(content)
    
    if not is_valid_image:
         raise HTTPException(status_code=400, detail=f"Invalid Proof of Delivery: {reason}")
    
    # 3. Update Database Status
    await delivery_service.update_package_status(db, package_id, "delivered", driver_id)
    DELIVERIES_COMPLETED.inc()
    
    # 4. Trigger Async Notification
    background_tasks.add_task(
        notification_service.send_notification,
        "customer_placeholder",
        "email@example.com",
        NotificationEvent.DELIVERY_COMPLETED,
    )
    
    return {"status": "success", "package_id": package_id}

@router.post("/exception")
async def report_exception(
    package_id: str = Form(...),
    driver_id: str = Form(...),
    reason: str = Form(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Update heartbeat
    driver_heartbeats[driver_id] = time.time()
    
    # Update status to exception
    await delivery_service.update_package_status(db, package_id, "exception", driver_id)
    
    return {"status": "exception_reported", "package_id": package_id, "reason": reason}



