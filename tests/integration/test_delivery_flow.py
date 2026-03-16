"""
Integration tests: Delivery flow
- POST /delivery/verify-location  → in-zone and out-of-zone cases
- POST /delivery/confirm          → marks package delivered (mocked image verifier)
- POST /delivery/exception        → marks package as exception
- GET  /delivery/recent-proofs    → manager can list proofs
"""
import io
import pytest
from unittest.mock import patch
from tests.integration.conftest import int_db_seed_driver, int_db_seed_package
from sqlalchemy import select
from src.backend.models.sql_models import Package as PackageSQL


@pytest.mark.asyncio
async def test_verify_location_in_zone(int_client_driver):
    """Driver within 200 m of target receives allowed=True."""
    client, db, drv = int_client_driver

    resp = await client.post("/delivery/verify-location", json={
        "driver_id": drv.id,
        "current_location":  {"lat": 40.7128, "lon": -74.0060},
        "target_delivery_location": {"lat": 40.7130, "lon": -74.0062},
    })
    assert resp.status_code == 200
    assert resp.json()["allowed"] is True


@pytest.mark.asyncio
async def test_verify_location_out_of_zone(int_client_driver):
    """Driver 50 km from target receives allowed=False."""
    client, db, drv = int_client_driver

    resp = await client.post("/delivery/verify-location", json={
        "driver_id": drv.id,
        "current_location":  {"lat": 40.7128, "lon": -74.0060},
        "target_delivery_location": {"lat": 41.1500, "lon": -74.5000},
    })
    assert resp.status_code == 200
    assert resp.json()["allowed"] is False


@pytest.mark.asyncio
async def test_confirm_delivery_marks_package_delivered(int_client_driver):
    """POST /delivery/confirm changes package status to delivered."""
    client, db, drv = int_client_driver
    pkg = await int_db_seed_package(db, driver_id=drv.id, status="pending")

    # Minimal valid JPEG (1x1 white pixel) so image_verifier gets real bytes
    minimal_jpeg = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x87"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00"
        b"\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00"
        b"\x08\x01\x01\x00\x00?\x00\xf5\x0a\xff\xd9"
    )

    with patch("src.analytics.image_analysis.verifier.image_verifier.verify_proof_of_delivery",
               return_value=(True, "mock-ok")):
        resp = await client.post(
            "/delivery/confirm",
            data={"package_id": pkg.id, "driver_id": drv.id},
            files={"photo": ("test.jpg", io.BytesIO(minimal_jpeg), "image/jpeg")},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # Verify DB state
    result = await db.execute(select(PackageSQL).where(PackageSQL.id == pkg.id))
    updated = result.scalar_one()
    assert updated.status == "delivered"


@pytest.mark.asyncio
async def test_confirm_delivery_invalid_image_rejected(int_client_driver):
    """A photo that fails image verification returns 400."""
    client, db, drv = int_client_driver
    pkg = await int_db_seed_package(db, driver_id=drv.id, status="pending")

    with patch("src.analytics.image_analysis.verifier.image_verifier.verify_proof_of_delivery",
               return_value=(False, "Image too blurry")):
        resp = await client.post(
            "/delivery/confirm",
            data={"package_id": pkg.id, "driver_id": drv.id},
            files={"photo": ("bad.jpg", io.BytesIO(b"notanimage"), "image/jpeg")},
        )

    assert resp.status_code == 400
    assert "Invalid Proof" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_report_exception(int_client_driver):
    """POST /delivery/exception marks package as exception."""
    client, db, drv = int_client_driver
    pkg = await int_db_seed_package(db, driver_id=drv.id, status="pending")

    resp = await client.post(
        "/delivery/exception",
        data={"package_id": pkg.id, "driver_id": drv.id, "reason": "Access denied"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "exception_reported"
    assert body["package_id"] == pkg.id

    # Verify DB state
    result = await db.execute(select(PackageSQL).where(PackageSQL.id == pkg.id))
    updated = result.scalar_one()
    assert updated.status == "exception"


@pytest.mark.asyncio
async def test_recent_proofs_accessible_by_manager(int_client_manager):
    """GET /delivery/recent-proofs returns 200 for managers."""
    client, db, mgr = int_client_manager

    resp = await client.get("/delivery/recent-proofs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
