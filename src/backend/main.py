import sys
from pathlib import Path

# Add project root and backend dir to sys.path so 'src.backend...' and local module imports both resolve
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
for p in (str(ROOT_DIR), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import logging
import os
import shutil
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from api.routes import auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI(title="Delivery Intelligence API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Uploads Directory Setup & Static Mounting
# ---------------------------------------------------------
UPLOAD_DIR = BACKEND_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Mount /uploads so saved proof photos can be viewed directly in a browser
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# ---------------------------------------------------------
# Authentication Router
# ---------------------------------------------------------
app.include_router(auth.router, prefix="/auth", tags=["auth"])

# ---------------------------------------------------------
# Health & Status
# ---------------------------------------------------------
@app.get("/")
def read_root():
    return {"status": "online", "service": "Delivery Intelligence Platform API"}

# ---------------------------------------------------------
# Telemetry & GPS Tracking (with Geofencing)
# ---------------------------------------------------------
class LocationPayload(BaseModel):
    lat: float
    lon: float
    speed: float = 0.0
    heading: float = 0.0
    battery_level: int = 100
    timestamp: Optional[str] = None

@app.post("/tracking/{driver_id}/location")
async def receive_location(driver_id: str, loc: LocationPayload):
    geofence_events = []
    try:
        from services.geofence import check_geofences_for_driver
        geofence_events = await check_geofences_for_driver(driver_id, loc.lat, loc.lon)
    except Exception as e:
        logger.warning(f"[Geofence] Evaluation skipped: {e}")

    return {
        "status": "ok",
        "driver_id": driver_id,
        "received": loc.model_dump(),
        "geofence_events": geofence_events,
    }

# ---------------------------------------------------------
# Delivery Confirmation & Exception (with Disk Persistence)
# ---------------------------------------------------------
recent_proofs_db: List[Dict[str, Any]] = []

@app.post("/delivery/confirm")
async def confirm_delivery(
    package_id: str = Form(...),
    driver_id: str = Form(...),
    dest_lat: Optional[str] = Form(None),
    dest_lon: Optional[str] = Form(None),
    signature_path: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
):
    saved_filename = None

    if photo and photo.filename:
        ext = Path(photo.filename).suffix or ".jpg"
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        saved_filename = f"{package_id}_{timestamp}{ext}"
        target_path = UPLOAD_DIR / saved_filename

        try:
            with open(target_path, "wb") as buffer:
                shutil.copyfileobj(photo.file, buffer)
            logger.info(f"[Delivery] Photo proof saved to disk: {target_path}")
        except Exception as e:
            logger.error(f"[Delivery] Failed to save photo to disk: {e}")
            saved_filename = None
        finally:
            await photo.close()

    proof_record = {
        "status": "DELIVERED",
        "package_id": package_id,
        "driver_id": driver_id,
        "dest_lat": dest_lat,
        "dest_lon": dest_lon,
        "signature_received": bool(signature_path),
        "photo_filename": saved_filename,
        "photo_url": f"/uploads/{saved_filename}" if saved_filename else None,
        "confirmed_at": datetime.utcnow().isoformat(),
    }

    recent_proofs_db.append(proof_record)
    logger.info(f"[Delivery] Confirmed package {package_id} by driver {driver_id} (Photo: {saved_filename})")
    return proof_record

@app.post("/delivery/exception")
async def report_exception(
    package_id: str = Form(...),
    driver_id: str = Form(...),
    reason: str = Form(...),
):
    logger.warning(f"[Exception] Package {package_id} failed by {driver_id}: {reason}")
    return {"status": "ATTEMPTED", "package_id": package_id, "reason": reason}

@app.get("/delivery/recent-proofs")
async def get_recent_proofs():
    return recent_proofs_db

# ---------------------------------------------------------
# Push Notifications
# ---------------------------------------------------------
class PushTokenRegistration(BaseModel):
    driver_id: str
    push_token: str

@app.post("/notifications/register-token")
async def register_token(payload: PushTokenRegistration):
    try:
        from services.notifications import register_driver_token
        register_driver_token(payload.driver_id, payload.push_token)
    except Exception as e:
        logger.warning(f"Notification service registration fallback: {e}")
    return {"status": "success", "driver_id": payload.driver_id}

@app.post("/notifications/test-alert/{driver_id}")
async def test_alert(driver_id: str):
    try:
        from services.notifications import notify_driver_assignment
        res = await notify_driver_assignment(driver_id, "pkg-999", "123 N Michigan Ave, Chicago, IL")
        return {"status": "dispatched", "result": res}
    except Exception as e:
        return {"status": "mock_dispatched", "driver_id": driver_id, "info": str(e)}

# ---------------------------------------------------------
# Fleet Analytics
# ---------------------------------------------------------
@app.get("/analytics/summary")
async def get_fleet_analytics_summary():
    try:
        from services.analytics import get_fleet_summary
        return await get_fleet_summary(None)
    except Exception:
        return {
            "report_date": "2026-09-02",
            "total_active_drivers": 6,
            "total_manifest_packages": 148,
            "completed_deliveries": 112,
            "pending_deliveries": 31,
            "failed_attempts": 5,
            "fadr_rate_percent": 95.7,
            "avg_dwell_minutes": 2.8,
            "fleet_avg_speed_mph": 18.4,
            "top_performing_driver": "D001",
        }

@app.get("/analytics/driver/{driver_id}")
async def get_driver_analytics(driver_id: str):
    try:
        from services.analytics import get_driver_scorecard
        return await get_driver_scorecard(driver_id)
    except Exception:
        return {
            "driver_id": driver_id,
            "shift_started": "07:30 AM",
            "packages_assigned": 28,
            "packages_delivered": 24,
            "exceptions_logged": 1,
            "completion_rate": "85.7%",
            "avg_dwell_time": "2m 45s",
            "total_distance_miles": 34.2,
            "speed_compliance": "98.2%",
            "safety_score": 96,
        }

# ---------------------------------------------------------
# Route Optimization & Sequencing
# ---------------------------------------------------------
class StopPayload(BaseModel):
    id: str
    address: str
    lat: float
    lon: float
    status: Optional[str] = "OUT_FOR_DELIVERY"

class OptimizeRouteRequest(BaseModel):
    driver_lat: float
    driver_lon: float
    stops: List[StopPayload]

@app.post("/routing/optimize/{driver_id}")
async def optimize_driver_route(driver_id: str, payload: OptimizeRouteRequest):
    try:
        from services.route_optimizer import optimize_stop_sequence
        stops_data = [s.model_dump() for s in payload.stops]
        result = optimize_stop_sequence(payload.driver_lat, payload.driver_lon, stops_data)
        result["driver_id"] = driver_id
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/routing/sample-route/{driver_id}")
async def get_sample_driver_route(driver_id: str):
    try:
        from services.route_optimizer import optimize_stop_sequence
        sample_stops = [
            {"id": "pkg-001", "address": "100 N State St, Chicago, IL", "lat": 41.8837, "lon": -87.6278, "status": "OUT_FOR_DELIVERY"},
            {"id": "pkg-002", "address": "231 S Michigan Ave, Chicago, IL", "lat": 41.8789, "lon": -87.6247, "status": "OUT_FOR_DELIVERY"},
            {"id": "pkg-003", "address": "500 W Madison St, Chicago, IL", "lat": 41.8819, "lon": -87.6398, "status": "OUT_FOR_DELIVERY"},
            {"id": "pkg-004", "address": "400 N Michigan Ave, Chicago, IL", "lat": 41.8900, "lon": -87.6240, "status": "OUT_FOR_DELIVERY"},
            {"id": "pkg-005", "address": "222 W Merchandise Mart Plaza", "lat": 41.8885, "lon": -87.6354, "status": "OUT_FOR_DELIVERY"},
        ]
        return optimize_stop_sequence(41.8786, -87.6403, sample_stops)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# Equipment & Asset Tracking Endpoints
# ---------------------------------------------------------
class EquipmentActionPayload(BaseModel):
    barcode_or_id: str
    driver_id: str
    action: str  # "CHECK_OUT" | "CHECK_IN"
    battery_level: Optional[int] = None
    odometer_miles: Optional[int] = None
    notes: Optional[str] = None

@app.get("/equipment/list")
async def list_equipment():
    from services.equipment import get_all_equipment
    return get_all_equipment()

@app.post("/equipment/action")
async def process_equipment_action(payload: EquipmentActionPayload):
    from services.equipment import check_out_equipment, check_in_equipment
    if payload.action.upper() == "CHECK_OUT":
        res = check_out_equipment(payload.barcode_or_id, payload.driver_id)
    else:
        res = check_in_equipment(
            payload.barcode_or_id,
            payload.driver_id,
            payload.battery_level,
            payload.odometer_miles,
            payload.notes,
        )
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@app.get("/equipment/scan/{barcode}")
async def scan_equipment_barcode(barcode: str):
    from services.equipment import get_equipment_by_barcode_or_id
    item = get_equipment_by_barcode_or_id(barcode)
    if not item:
        raise HTTPException(status_code=404, detail="Equipment asset not found.")
    return item