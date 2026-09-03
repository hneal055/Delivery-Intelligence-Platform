import csv
import io
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "delivery_proofs.db"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Delivery Intelligence Platform API",
    version="1.0.0",
    description="Backend routing, proof-of-delivery logging, and telemetry ingestion.",
)

# Enable CORS for Metro, emulator, and web environments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded delivery proof photos statically
app.mount("/static/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS delivery_proofs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id TEXT NOT NULL,
            driver_id TEXT NOT NULL,
            status TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            dest_lat REAL,
            dest_lon REAL,
            signature_path TEXT,
            photo_filename TEXT
        )
        """
    )
    conn.commit()
    conn.close()


# Initialize SQLite table schema on startup
init_db()


@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/routing/sample-route/{driver_id}")
def get_sample_route(driver_id: str):
    """
    Returns an optimized delivery sequence for a driver.
    """
    stops = [
        {"id": "pkg-001", "address": "100 N State St, Chicago, IL", "lat": 41.8837, "lon": -87.6278},
        {"id": "pkg-002", "address": "231 S Michigan Ave, Chicago, IL", "lat": 41.8789, "lon": -87.6247},
        {"id": "pkg-003", "address": "500 W Madison St, Chicago, IL", "lat": 41.8819, "lon": -87.6398},
        {"id": "pkg-004", "address": "400 N Michigan Ave, Chicago, IL", "lat": 41.8900, "lon": -87.6240},
        {"id": "pkg-005", "address": "222 W Merchandise Mart Plaza", "lat": 41.8885, "lon": -87.6354},
    ]
    return {
        "driver_id": driver_id,
        "total_stops": len(stops),
        "ordered_stops": stops,
    }


@app.post("/delivery/confirm")
async def confirm_delivery(
    package_id: str = Form(...),
    driver_id: str = Form("D001"),
    dest_lat: float = Form(41.8786),
    dest_lon: float = Form(-87.6403),
    signature_path: Optional[str] = Form(None),
    status: str = Form("DELIVERED"),
    photo: Optional[UploadFile] = File(None),
):
    """
    Receives proof-of-delivery data with multipart binary photo proof.
    """
    saved_filename = None
    if photo and photo.filename:
        ext = Path(photo.filename).suffix or ".jpg"
        clean_ext = ext if ext.lower() in [".jpg", ".jpeg", ".png"] else ".jpg"
        saved_filename = f"{package_id}_{int(datetime.utcnow().timestamp())}{clean_ext}"
        destination = UPLOADS_DIR / saved_filename

        with open(destination, "wb") as buffer:
            content = await photo.read()
            buffer.write(content)

    timestamp = datetime.utcnow().isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO delivery_proofs (
            package_id, driver_id, status, timestamp, 
            dest_lat, dest_lon, signature_path, photo_filename
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            package_id,
            driver_id,
            status,
            timestamp,
            dest_lat,
            dest_lon,
            signature_path,
            saved_filename,
        ),
    )
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()

    return {
        "success": True,
        "record_id": record_id,
        "package_id": package_id,
        "status": status,
        "timestamp": timestamp,
        "photo_url": f"/static/uploads/{saved_filename}" if saved_filename else None,
    }


@app.get("/delivery/recent-proofs")
def get_recent_proofs(limit: int = Query(20, ge=1, le=100)):
    """
    Returns recent delivery proof records ordered by recency.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, package_id, driver_id, status, timestamp, 
               dest_lat, dest_lon, signature_path, photo_filename
        FROM delivery_proofs
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "package_id": r["package_id"],
            "driver_id": r["driver_id"],
            "status": r["status"],
            "timestamp": r["timestamp"],
            "dest_lat": r["dest_lat"],
            "dest_lon": r["dest_lon"],
            "signature_path": r["signature_path"],
            "photo_url": f"/static/uploads/{r['photo_filename']}" if r["photo_filename"] else None,
        }
        for r in rows
    ]


@app.get("/delivery/export")
def export_delivery_proofs(
    format: str = Query("json", regex="^(json|csv)$", description="Export format: 'json' or 'csv'"),
    driver_id: Optional[str] = Query(None, description="Filter by driver ID (e.g. 'D001')"),
):
    """
    Export all logged delivery proofs as a downloadable JSON or CSV file.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if driver_id:
        cursor.execute(
            """
            SELECT id, package_id, driver_id, status, timestamp, 
                   dest_lat, dest_lon, signature_path, photo_filename
            FROM delivery_proofs
            WHERE driver_id = ?
            ORDER BY id DESC
            """,
            (driver_id,),
        )
    else:
        cursor.execute(
            """
            SELECT id, package_id, driver_id, status, timestamp, 
                   dest_lat, dest_lon, signature_path, photo_filename
            FROM delivery_proofs
            ORDER BY id DESC
            """
        )

    rows = cursor.fetchall()
    conn.close()

    records = [
        {
            "id": r["id"],
            "package_id": r["package_id"],
            "driver_id": r["driver_id"],
            "status": r["status"],
            "timestamp": r["timestamp"],
            "latitude": r["dest_lat"],
            "longitude": r["dest_lon"],
            "signature_path": r["signature_path"],
            "photo_filename": r["photo_filename"],
        }
        for r in rows
    ]

    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    target_suffix = f"_{driver_id}" if driver_id else "_all"

    # CSV Export
    if format.lower() == "csv":
        output = io.StringIO()
        fieldnames = [
            "id",
            "package_id",
            "driver_id",
            "status",
            "timestamp",
            "latitude",
            "longitude",
            "signature_path",
            "photo_filename",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

        filename = f"delivery_proofs{target_suffix}_{timestamp_str}.csv"
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # JSON Export
    filename = f"delivery_proofs{target_suffix}_{timestamp_str}.json"
    return Response(
        content=json.dumps(records, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/debug/reset-db")
def reset_database():
    """
    Clears all delivery proofs from SQLite and removes uploaded proof images.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM delivery_proofs")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='delivery_proofs'")
    conn.commit()
    conn.close()

    # Clean up stored upload images
    deleted_files = 0
    for file_path in UPLOADS_DIR.glob("*.*"):
        try:
            file_path.unlink()
            deleted_files += 1
        except OSError:
            pass

    return {
        "status": "success",
        "message": "All proofs cleared and SQLite autoincrement sequence reset.",
        "deleted_photos": deleted_files,
    }