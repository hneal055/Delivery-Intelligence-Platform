import logging
import time
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.geofencing.engine import geofence_engine
from src.analytics.image_analysis.verifier import image_verifier
from src.backend.api.deps import get_current_active_user
from src.backend.api.limiter import limiter
from src.backend.api.metrics import DELIVERIES_COMPLETED, driver_heartbeats
from src.backend.core.database import get_db
from src.backend.core.storage import is_safe_filename, proof_storage
from src.backend.models.domain import Location, User, UserRole
from src.backend.models.sql_models import DeliveryProof, Package
from src.backend.services import delivery_service
from src.backend.services.notifications import (
    NotificationEvent,
    notification_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/delivery", tags=["delivery"])

# A scan moves a package into the van only from these states; a delivered
# or exception package keeps its status so a stray rescan cannot undo it.
LOADABLE_STATUSES = {"pending", "assigned"}

# SVG path data from the in-app signature pad; generous but bounded.
MAX_SIGNATURE_CHARS = 100_000


async def _get_package(db: AsyncSession, package_id: str) -> Optional[Package]:
    result = await db.execute(select(Package).where(Package.id == package_id))
    return result.scalars().first()


# A package in one of these states has been closed out by a driver.
FINAL_STATUSES = {"delivered", "exception"}


def _acting_driver(current_user: User, claimed_driver_id: str) -> str:
    """Who the delivery is recorded against. A driver is always themselves
    (their username is their driver ID), whatever the form says; office
    roles may record on behalf of the named driver."""
    if current_user.role == UserRole.DRIVER:
        return current_user.username
    return claimed_driver_id


def _check_can_close(current_user: User, package: Package) -> None:
    """Drivers may only close out packages assigned to them, and nobody may
    close a package twice."""
    if current_user.role == UserRole.DRIVER and package.driver_id != current_user.username:
        raise HTTPException(status_code=403, detail="Package is not assigned to you")
    if package.status in FINAL_STATUSES:
        raise HTTPException(
            status_code=409, detail=f"Package already {package.status}"
        )


@router.get("/recent-proofs")
async def get_recent_proofs(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    """Newest accepted proofs. Drivers see only their own."""
    query = select(DeliveryProof).order_by(DeliveryProof.captured_at.desc())
    if current_user.role == UserRole.DRIVER:
        query = query.where(DeliveryProof.driver_id == current_user.username)
    result = await db.execute(query.limit(limit))
    return [
        {
            "packageId": proof.package_id,
            "driverId": proof.driver_id,
            "timestamp": proof.captured_at.isoformat() if proof.captured_at else None,
            "filename": proof.photo_key,
            "url": "/delivery/proof/" + proof.photo_key,
            "lat": proof.lat,
            "lon": proof.lon,
            "distanceMeters": proof.distance_m,
            "signature": proof.signature_svg,
        }
        for proof in result.scalars().all()
    ]


@router.get("/proof/{filename}")
async def get_proof_image(
    filename: str,
    current_user: User = Depends(get_current_active_user),
):
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
):
    driver_id = (
        payload.driver_id
        if payload.driver_id != "unknown"
        else current_user.username
    )
    driver_heartbeats[driver_id] = time.time()

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


class ScanRequest(BaseModel):
    barcode: str
    scan_type: Optional[str] = None


@router.post("/scan")
async def scan_package(
    payload: ScanRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Load a package into the van by its ID or tracking code."""
    barcode = payload.barcode.strip()
    result = await db.execute(
        select(Package).where(
            or_(Package.id == barcode, Package.tracking_code == barcode)
        )
    )
    package = result.scalars().first()
    if package is None:
        raise HTTPException(status_code=404, detail="Package not found")

    if package.status in LOADABLE_STATUSES:
        package.status = "loaded"
        package.loaded_at = datetime.now(timezone.utc)
        await db.commit()

    return {
        "status": "success",
        "package_id": package.id,
        "package_status": package.status,
        "dest_address": package.dest_address,
    }


@router.post("/confirm")
async def confirm_delivery(
    package_id: str = Form(...),
    driver_id: str = Form(...),
    photo: UploadFile = File(...),
    dest_lat: Optional[float] = Form(None),
    dest_lon: Optional[float] = Form(None),
    signature_path: Optional[str] = Form(None, max_length=MAX_SIGNATURE_CHARS),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    driver_id = _acting_driver(current_user, driver_id)
    driver_heartbeats[driver_id] = time.time()
    content = await photo.read()

    # 1. Only real packages can be delivered; never invent one. The photo of
    #    an unknown package is still kept as evidence.
    package = await _get_package(db, package_id)
    if package is None:
        await proof_storage.save_proof(package_id, driver_id, content)
        raise HTTPException(status_code=404, detail="Package not found")

    # 2. Not someone else's package, and not already closed (this also makes
    #    a resent upload a harmless 409 instead of a duplicate proof).
    _check_can_close(current_user, package)

    # 3. Persist the proof before the quality check: a rejected photo is
    #    still evidence and stays in storage.
    saved_filename = await proof_storage.save_proof(package_id, driver_id, content)

    # 4. Quality check (blur/darkness). Reject so the driver retakes,
    #    but the original stays in storage.
    is_valid_image, reason = image_verifier.verify_proof_of_delivery(content)
    if not is_valid_image:
        raise HTTPException(
            status_code=400,
            detail="Invalid Proof of Delivery: {0}".format(reason),
        )

    # 5. Record where the driver was. Recorded, not enforced: offline
    #    captures can arrive without a fresh fix.
    distance = None
    if dest_lat is not None and dest_lon is not None:
        _, distance = geofence_engine.verify_delivery_location(
            (dest_lat, dest_lon), (package.dest_lat, package.dest_lon)
        )
        logger.info(
            "Package %s confirmed %.0fm from its destination", package_id, distance
        )

    db.add(
        DeliveryProof(
            package_id=package_id,
            driver_id=driver_id,
            photo_key=saved_filename,
            signature_svg=signature_path or None,
            lat=dest_lat,
            lon=dest_lon,
            distance_m=distance,
        )
    )
    await delivery_service.update_package_status(
        db, package_id, "delivered", driver_id
    )
    await delivery_service.complete_dispatch_job(db, package_id)
    DELIVERIES_COMPLETED.inc()

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
    driver_id = _acting_driver(current_user, driver_id)
    driver_heartbeats[driver_id] = time.time()
    package = await _get_package(db, package_id)
    if package is None:
        raise HTTPException(status_code=404, detail="Package not found")
    _check_can_close(current_user, package)

    await delivery_service.update_package_status(
        db, package_id, "exception", driver_id
    )
    logger.info("Exception on package %s: %s", package_id, reason)
    return {
        "status": "exception_reported",
        "package_id": package_id,
        "reason": reason,
    }
