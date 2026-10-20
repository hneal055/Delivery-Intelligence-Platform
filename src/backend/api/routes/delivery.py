import logging
import time
from datetime import datetime, timezone
from typing import Optional

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
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.geofencing.engine import geofence_engine
from src.analytics.image_analysis.verifier import image_verifier
from src.backend.api.deps import PermissionChecker, get_current_active_user
from src.backend.api.limiter import limiter
from src.backend.api.metrics import DELIVERIES_COMPLETED, driver_heartbeats
from src.backend.core.database import get_db
from src.backend.core.permissions import Permission
from src.backend.core.storage import is_safe_filename, proof_storage
from src.backend.models.domain import Location, User, UserRole
from src.backend.models.sql_models import DeliveryProof, Package
from src.backend.services import customer_updates, delivery_service
from src.backend.services.redis_manager import manager as ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/delivery", tags=["delivery"])

LOADABLE_STATUSES = {"pending", "assigned"}
FINAL_STATUSES = {"delivered", "exception"}
MAX_SIGNATURE_CHARS = 100_000
MAX_PROOF_BYTES = 10 * 1024 * 1024


async def _get_package(db: AsyncSession, package_id: str) -> Optional[Package]:
    result = await db.execute(
        select(Package).where(Package.id == package_id).with_for_update()
    )
    return result.scalars().first()


def _acting_driver(current_user: User, claimed_driver_id: str) -> str:
    if current_user.role == UserRole.DRIVER:
        return current_user.username
    return claimed_driver_id


def _check_can_close(current_user: User, package: Package) -> None:
    if (
        current_user.role == UserRole.DRIVER
        and package.driver_id != current_user.username
    ):
        raise HTTPException(status_code=403, detail="Package is not assigned to you")
    if package.status in FINAL_STATUSES:
        raise HTTPException(
            status_code=409, detail=f"Package already {package.status}"
        )


async def _read_proof(photo: UploadFile) -> bytes:
    if photo.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=415, detail="Proof must be a JPEG or PNG image")
    content = await photo.read(MAX_PROOF_BYTES + 1)
    if len(content) > MAX_PROOF_BYTES:
        raise HTTPException(status_code=413, detail="Proof image exceeds 10 MB")
    if not content:
        raise HTTPException(status_code=400, detail="Proof image is empty")
    return content


@router.get("/recent-proofs")
async def get_recent_proofs(
    limit: int = Query(50, ge=1, le=200),
    package_id: Optional[str] = Query(None, min_length=1, max_length=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return recent accepted proofs; drivers can see only their own."""
    query = select(DeliveryProof).order_by(DeliveryProof.captured_at.desc())
    if package_id:
        query = query.where(DeliveryProof.package_id == package_id)
    if current_user.role == UserRole.DRIVER:
        query = query.where(DeliveryProof.driver_id == current_user.username)
    result = await db.execute(query.limit(limit))
    return [
        {
            "packageId": proof.package_id,
            "driverId": proof.driver_id,
            "timestamp": proof.captured_at.isoformat() if proof.captured_at else None,
            "filename": proof.photo_key,
            "url": f"/delivery/proof/{proof.photo_key}",
            "lat": proof.lat,
            "lon": proof.lon,
            "distanceMeters": proof.distance_m,
            "signature": proof.signature_svg,
            "receivedBy": proof.received_by,
        }
        for proof in result.scalars().all()
    ]


@router.get("/proof/{filename}")
async def get_proof_image(
    filename: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if not is_safe_filename(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if current_user.role == UserRole.DRIVER:
        owned = await db.execute(
            select(DeliveryProof.id).where(
                DeliveryProof.photo_key == filename,
                DeliveryProof.driver_id == current_user.username,
            )
        )
        if owned.first() is None:
            raise HTTPException(status_code=404, detail="Image not found")

    data = await proof_storage.get_proof(filename)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")
    media_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
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
    driver_id = _acting_driver(current_user, payload.driver_id)
    if driver_id == "unknown":
        driver_id = current_user.username
    driver_heartbeats[driver_id] = time.time()

    is_valid, distance = geofence_engine.verify_delivery_location(
        (payload.current_location.lat, payload.current_location.lon),
        (
            payload.target_delivery_location.lat,
            payload.target_delivery_location.lon,
        ),
    )
    if is_valid:
        return {"message": "Location Verified", "allowed": True, "distance": distance}
    return {
        "message": f"Driver is too far ({distance:.2f}m) from delivery point",
        "allowed": False,
        "distance": distance,
    }


class ScanRequest(BaseModel):
    barcode: str = Field(min_length=1, max_length=200)
    scan_type: Optional[str] = None


@router.post("/scan")
async def scan_package(
    payload: ScanRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(PermissionChecker(Permission.UPDATE_PACKAGE_STATUS)),
    db: AsyncSession = Depends(get_db),
):
    """Load an assigned package into the van by its ID or tracking code."""
    barcode = payload.barcode.strip()
    if not barcode:
        raise HTTPException(status_code=422, detail="Barcode cannot be blank")
    result = await db.execute(
        select(Package).where(
            or_(Package.id == barcode, Package.tracking_code == barcode)
        )
    )
    package = result.scalars().first()
    if package is None:
        raise HTTPException(status_code=404, detail="Package not found")

    if package.status in LOADABLE_STATUSES:
        if current_user.role == UserRole.DRIVER and package.driver_id not in (
            None,
            current_user.username,
        ):
            raise HTTPException(status_code=403, detail="Package is not assigned to you")
        if current_user.role == UserRole.DRIVER and package.driver_id is None:
            package.driver_id = current_user.username
        package.status = "loaded"
        package.loaded_at = datetime.now(timezone.utc)
        customer_updates.queue_out_for_delivery(background_tasks, package)
        await db.commit()

    return {
        "status": "success",
        "package_id": package.id,
        "package_status": package.status,
        "dest_address": package.dest_address,
    }


@router.post("/confirm")
async def confirm_delivery(
    background_tasks: BackgroundTasks,
    package_id: str = Form(..., min_length=1, max_length=200),
    driver_id: str = Form(..., min_length=1, max_length=200),
    photo: UploadFile = File(...),
    dest_lat: Optional[float] = Form(None, ge=-90, le=90),
    dest_lon: Optional[float] = Form(None, ge=-180, le=180),
    signature_path: Optional[str] = Form(None, max_length=MAX_SIGNATURE_CHARS),
    received_by: Optional[str] = Form(None, max_length=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if (dest_lat is None) != (dest_lon is None):
        raise HTTPException(
            status_code=422, detail="Both destination coordinates must be provided"
        )

    driver_id = _acting_driver(current_user, driver_id)
    driver_heartbeats[driver_id] = time.time()
    content = await _read_proof(photo)
    extension = ".png" if photo.content_type == "image/png" else ".jpg"
    package = await _get_package(db, package_id)

    if package is None:
        await proof_storage.save_proof(package_id, driver_id, content, extension)
        raise HTTPException(status_code=404, detail="Package not found")

    _check_can_close(current_user, package)
    saved_filename = await proof_storage.save_proof(
        package_id, driver_id, content, extension
    )

    is_valid_image, reason = image_verifier.verify_proof_of_delivery(content)
    if not is_valid_image:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Proof of Delivery: {reason}",
        )

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
            received_by=(received_by or "").strip() or None,
            lat=dest_lat,
            lon=dest_lon,
            distance_m=distance,
        )
    )
    customer_updates.queue_delivered(
        background_tasks, package, datetime.now(timezone.utc)
    )
    await delivery_service.update_package_status(
        db, package_id, "delivered", driver_id
    )
    await delivery_service.complete_dispatch_job(db, package_id)
    try:
        await ws_manager.broadcast_to_dispatchers(
            {"type": "package_updated", "package_id": package_id}
        )
    except Exception as exc:
        logger.warning("Could not broadcast delivery update for %s: %s", package_id, exc)
    DELIVERIES_COMPLETED.inc()

    return {"status": "success", "package_id": package_id, "proof": saved_filename}


@router.post("/exception")
async def report_exception(
    package_id: str = Form(..., min_length=1, max_length=200),
    driver_id: str = Form(..., min_length=1, max_length=200),
    reason: str = Form(..., min_length=2, max_length=500),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    driver_id = _acting_driver(current_user, driver_id)
    driver_heartbeats[driver_id] = time.time()
    package = await _get_package(db, package_id)
    if package is None:
        raise HTTPException(status_code=404, detail="Package not found")
    _check_can_close(current_user, package)

    normalized_reason = reason.strip()
    if len(normalized_reason) < 2:
        raise HTTPException(
            status_code=422, detail="Reason must contain at least 2 non-space characters"
        )
    package.exception_reason = normalized_reason
    await delivery_service.update_package_status(
        db, package_id, "exception", driver_id
    )
    logger.info("Exception on package %s: %s", package_id, package.exception_reason)
    try:
        await ws_manager.broadcast_to_dispatchers(
            {
                "type": "problem_reported",
                "package_id": package_id,
                "driver_id": driver_id,
                "reason": package.exception_reason,
                "address": package.dest_address,
            }
        )
    except Exception as exc:
        logger.warning("Could not broadcast problem report: %s", exc)
    return {
        "status": "exception_reported",
        "package_id": package_id,
        "reason": package.exception_reason,
    }
