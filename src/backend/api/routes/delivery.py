import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
import redis.asyncio as aioredis
from src.backend.api.routes.geofence import verify_geofence, GeofenceCheckRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# Target the Docker volume mounted at /app/uploads
UPLOADS_DIR = Path("/app/uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = Path("/app/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "delivery_proofs.db"

REDIS_URL = os.getenv("REDIS_URL", "redis://delivery_redis:6379")

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

async def publish_delivery_event(package_id: str, driver_id: str, status: str):
    try:
        client = aioredis.from_url(REDIS_URL, decode_responses=True)
        await client.publish("fleet_events", f"Package {package_id} delivered by {driver_id}: {status}")
        await client.close()
    except Exception as e:
        logger.error(f"Failed to publish Redis event: {e}")

class DeliverySubmission(BaseModel):
    package_id: str
    driver_id: str
    status: str
    dest_lat: float
    dest_lon: float
    target_lat: float
    target_lon: float
    radius_meters: float = 150.0

@router.post("/submit")
async def submit_delivery(
    package_id: str = Form(...),
    driver_id: str = Form(...),
    status: str = Form(...),
    dest_lat: float = Form(...),
    dest_lon: float = Form(...),
    target_lat: float = Form(...),
    target_lon: float = Form(...),
    radius_meters: float = Form(150.0),
    signature: Optional[UploadFile] = File(None),
    photo: Optional[UploadFile] = File(None)
):
    """Submit proof of delivery with integrated geofence verification and Redis event broadcasting."""
    try:
        # 1. Verify geofence before accepting delivery
        geofence_req = GeofenceCheckRequest(
            driver_id=driver_id,
            latitude=dest_lat,
            longitude=dest_lon,
            target_latitude=target_lat,
            target_longitude=target_lon,
            radius_meters=radius_meters
        )
        geo_result = await verify_geofence(geofence_req)
        
        if not geo_result.get("is_inside", False):
            logger.warning(f"Delivery submission rejected for package {package_id}: driver outside geofence radius ({geo_result.get('distance_meters')}m).")
            raise HTTPException(
                status_code=400,
                detail=f"Geofence validation failed: Driver is {geo_result.get('distance_meters')}m away from target (max allowed: {radius_meters}m)."
            )

        # 2. Handle file uploads
        signature_filename = None
        if signature:
            signature_path = UPLOADS_DIR / f"sig_{package_id}_{signature.filename}"
            with open(signature_path, "wb") as buffer:
                buffer.write(await signature.read())
            signature_filename = str(signature_path.name)

        photo_filename = None
        if photo:
            photo_path = UPLOADS_DIR / f"photo_{package_id}_{photo.filename}"
            with open(photo_path, "wb") as buffer:
                buffer.write(await photo.read())
            photo_filename = str(photo_path.name)

        # 3. Save proof of delivery to database
        conn = get_db()
        try:
            conn.execute(
                """
                INSERT INTO delivery_proofs (
                    package_id, driver_id, status, timestamp, dest_lat, dest_lon, signature_path, photo_filename
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    package_id,
                    driver_id,
                    status,
                    datetime.now(timezone.utc).isoformat(),
                    dest_lat,
                    dest_lon,
                    signature_filename,
                    photo_filename
                )
            )
            conn.commit()
        finally:
            conn.close()

        # 4. Broadcast event via Redis Pub/Sub
        await publish_delivery_event(package_id, driver_id, status)

        logger.info(f"Delivery proof recorded and broadcasted successfully for package {package_id} by driver {driver_id}")
        return {
            "status": "success",
            "message": "Delivery proof recorded successfully with geofence validation and event broadcast.",
            "package_id": package_id,
            "geofence_distance_meters": geo_result.get("distance_meters")
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error submitting delivery proof: {e}")
        raise HTTPException(status_code=500, detail=str(e))