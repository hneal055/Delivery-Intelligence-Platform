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
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.models.domain import Location, Driver, User
from src.analytics.geofencing.engine import geofence_engine
from src.analytics.image_analysis.verifier import image_verifier
from src.backend.api.deps import get_current_active_user
from src.backend.services.notifications import notification_service, NotificationEvent
from src.backend.services import delivery_service
from src.backend.services.storage import proof_storage, LocalStorageBackend
from src.backend.api.limiter import limiter
from src.backend.api.metrics import DELIVERIES_COMPLETED
from src.backend.services.heartbeat import heartbeat_service
from src.backend.core.database import get_db

router = APIRouter(prefix="/delivery", tags=["delivery"])


@router.get("/recent-proofs")
async def get_recent_proofs() -> List[dict]:
    files = proof_storage.list_files()
    results = []
    for entry in files:
        key = entry["key"]
        parts = key.rsplit(".", 1)[0].split("_")
        pkg_id = parts[0] if len(parts) > 0 else "Unknown"
        driver_id = parts[1] if len(parts) > 1 else "Unknown"
        results.append({
            "packageId": pkg_id,
            "driverId": driver_id,
            "timestamp": entry["last_modified"].isoformat() if hasattr(entry["last_modified"], "isoformat") else str(entry["last_modified"]),
            "filename": key,
            "url": proof_storage.get_url(key),
        })
    return results


@router.get("/proof/{filename}")
async def get_proof_image(filename: str):
    if isinstance(proof_storage, LocalStorageBackend):
        path = proof_storage.get_file_path(filename)
        if not path:
            raise HTTPException(status_code=404, detail="Image not found")
        return FileResponse(path, media_type="image/jpeg")
    # S3 mode: redirect to presigned URL
    url = proof_storage.get_url(filename)
    return RedirectResponse(url=url)


# Schema for the request body
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
    db: AsyncSession = Depends(get_db)
):
    driver_id = payload.driver_id if payload.driver_id != "unknown" else current_user.username
    await heartbeat_service.update(driver_id)

    await delivery_service.update_driver_location(
        db,
        driver_id,
        payload.current_location.lat,
        payload.current_location.lon
    )

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
    await heartbeat_service.update(driver_id)

    # 1. Read file content
    content = await photo.read()

    # 2. Save Proof of Delivery via storage backend (local or S3)
    storage_key = f"{package_id}_{driver_id}.jpg"
    proof_storage.upload(storage_key, content, "image/jpeg")

    # 3. Verify Image (Blur/Darkness)
    is_valid_image, reason = image_verifier.verify_proof_of_delivery(content)
    if not is_valid_image:
        raise HTTPException(status_code=400, detail=f"Invalid Proof of Delivery: {reason}")

    # 4. Update Database Status
    await delivery_service.update_package_status(db, package_id, "delivered", driver_id)
    DELIVERIES_COMPLETED.inc()

    # 5. Trigger Async Notification
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
    await heartbeat_service.update(driver_id)
    await delivery_service.update_package_status(db, package_id, "exception", driver_id)
    return {"status": "exception_reported", "package_id": package_id, "reason": reason}
