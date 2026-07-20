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
from fastapi.responses import Response
from pydantic import BaseModel
import time
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.models.domain import Location, User
from src.analytics.geofencing.engine import geofence_engine
from src.analytics.image_analysis.verifier import image_verifier
from src.backend.api.deps import get_current_active_user
from src.backend.services.notifications import (
    notification_service,
    NotificationEvent,
)
from src.backend.services import delivery_service
from src.backend.api.limiter import limiter
from src.backend.api.metrics import driver_heartbeats, DELIVERIES_COMPLETED
from src.backend.core.database import get_db
from src.backend.core.storage import proof_storage, is_safe_filename

router = APIRouter(prefix="/delivery", tags=["delivery"])


@router.get("/recent-proofs")
async def get_recent_proofs() -> List[dict]:
    return await proof_storage.list_recent(limit=50)


@router.get("/proof/{filename}")
async def get_proof_image(filename: str):
    if not is_safe_filename(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    data = await proof_storage.get_proof(filename)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")
    media_type = (
        "image/png" if filename.lower().endswith(".png") else "image/jpeg"
    )
    return Response(content=data, media_type=media_type)


class LocationVerifyRequest(BaseModel):
    driver_id: str = "unknown"
    current_location: Location
    target_delivery_location: Location


@router.post("/verify-location")
@limiter.limit("1000/minute")
async def verify_location(
    request: Request,
    payload: LocationVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    driver_id = (
        payload.driver_id
        if payload.driver_id != "unknown"
        else current_user.username
    )
    driver_heartbeats[driver_id] = time.time()

    await delivery_service.update_driver_location(
        db,
        driver_id,
        payload.current_location.lat,
        payload.current_location.lon,
    )

    is_valid, distance = geofence_engine.verify_delivery_location(
        (payload.current_location.lat, payload.current_location.lon),
        (
            payload.target_delivery_location.lat,
            payload.target_delivery_location.lon,
        ),
    )

    if is_valid:
        return {
            "message": "Location Verified",
            "allowed": True,
            "distance": distance,
        }
    return {
        "message": "Driver is too far ({0:.2f}m) from delivery point".format(
            distance
        ),
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
    db: AsyncSession = Depends(get_db),
):
    driver_heartbeats[driver_id] = time.time()

    # 1. Read the uploaded photo
    content = await photo.read()

    # 2. Persist the proof FIRST -- it is legal evidence and must survive
    #    even if the quality check below rejects it and asks for a retake.
    saved_filename = await proof_storage.save_proof(
        package_id, driver_id, content
    )

    # 3. Quality check (blur/darkness). Reject so the driver retakes,
    #    but the original stays in storage.
    is_valid_image, reason = image_verifier.verify_proof_of_delivery(content)
    if not is_valid_image:
        raise HTTPException(
            status_code=400,
            detail="Invalid Proof of Delivery: {0}".format(reason),
        )

    # 4. Mark delivered
    await delivery_service.update_package_status(
        db, package_id, "delivered", driver_id
    )
    DELIVERIES_COMPLETED.inc()

    # 5. Async customer notification
    background_tasks.add_task(
        notification_service.send_notification,
        "customer_placeholder",
        "email@example.com",
        NotificationEvent.DELIVERY_COMPLETED,
    )

    return {
        "status": "success",
        "package_id": package_id,
        "proof": saved_filename,
    }


@router.post("/exception")
async def report_exception(
    package_id: str = Form(...),
    driver_id: str = Form(...),
    reason: str = Form(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    driver_heartbeats[driver_id] = time.time()
    await delivery_service.update_package_status(
        db, package_id, "exception", driver_id
    )
    return {
        "status": "exception_reported",
        "package_id": package_id,
        "reason": reason,
    }
