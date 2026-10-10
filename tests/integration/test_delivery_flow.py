"""
Integration tests: Delivery flow
- POST /delivery/verify-location  → in-zone and out-of-zone cases
- POST /delivery/confirm          → marks package delivered (mocked image verifier)
- POST /delivery/exception        → marks package as exception
- GET  /delivery/recent-proofs    → manager can list proofs
- POST /delivery/scan             → loads a package into the van
"""
import io
import pytest
from unittest.mock import patch
from tests.integration.conftest import int_db_seed_driver, int_db_seed_package
from sqlalchemy import select
from src.backend.core.storage import proof_storage
from src.backend.models.sql_models import DispatchJob, Package as PackageSQL


@pytest.fixture(autouse=True)
def _proofs_in_tmp(tmp_path, monkeypatch):
    """Keep test photos out of the real proof store."""
    monkeypatch.setattr(proof_storage, "base_dir", str(tmp_path))
    return tmp_path


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


@pytest.mark.asyncio
async def test_confirm_completes_dispatch_job(int_client_driver):
    """Confirming delivery closes the dispatch job linked to the package."""
    client, db, drv = int_client_driver
    pkg = await int_db_seed_package(db, status="pending")
    job = DispatchJob(title="Drop", package_id=pkg.id, status="assigned")
    db.add(job)
    await db.commit()

    with patch("src.analytics.image_analysis.verifier.image_verifier.verify_proof_of_delivery",
               return_value=(True, "mock-ok")):
        resp = await client.post(
            "/delivery/confirm",
            data={"package_id": pkg.id, "driver_id": drv.id},
            files={"photo": ("p.jpg", io.BytesIO(b"jpeg"), "image/jpeg")},
        )

    assert resp.status_code == 200
    await db.refresh(job)
    assert job.status == "completed"
    assert job.completed_at is not None


@pytest.mark.asyncio
async def test_confirm_unknown_package_returns_404_and_keeps_photo(int_client_driver, _proofs_in_tmp):
    """An unknown package is not invented, but the photo is still kept as evidence."""
    client, db, drv = int_client_driver

    with patch("src.analytics.image_analysis.verifier.image_verifier.verify_proof_of_delivery",
               return_value=(True, "mock-ok")):
        resp = await client.post(
            "/delivery/confirm",
            data={"package_id": "no-such-package", "driver_id": drv.id},
            files={"photo": ("p.jpg", io.BytesIO(b"jpeg"), "image/jpeg")},
        )

    assert resp.status_code == 404
    result = await db.execute(select(PackageSQL).where(PackageSQL.id == "no-such-package"))
    assert result.scalar_one_or_none() is None
    assert len(list(_proofs_in_tmp.iterdir())) == 1


@pytest.mark.asyncio
async def test_rejected_photo_is_still_stored(int_client_driver, _proofs_in_tmp):
    """A photo that fails the quality check is kept; the package stays undelivered."""
    client, db, drv = int_client_driver
    pkg = await int_db_seed_package(db, status="pending")

    with patch("src.analytics.image_analysis.verifier.image_verifier.verify_proof_of_delivery",
               return_value=(False, "Image too dark")):
        resp = await client.post(
            "/delivery/confirm",
            data={"package_id": pkg.id, "driver_id": drv.id},
            files={"photo": ("p.jpg", io.BytesIO(b"jpeg"), "image/jpeg")},
        )

    assert resp.status_code == 400
    assert len(list(_proofs_in_tmp.iterdir())) == 1
    await db.refresh(pkg)
    assert pkg.status == "pending"


@pytest.mark.asyncio
async def test_recent_proofs_lists_saved_photo(int_client_driver):
    """A confirmed delivery shows up in recent-proofs with a viewable image."""
    client, db, drv = int_client_driver
    pkg = await int_db_seed_package(db, status="pending")

    with patch("src.analytics.image_analysis.verifier.image_verifier.verify_proof_of_delivery",
               return_value=(True, "mock-ok")):
        await client.post(
            "/delivery/confirm",
            data={"package_id": pkg.id, "driver_id": drv.id},
            files={"photo": ("p.jpg", io.BytesIO(b"jpeg-bytes"), "image/jpeg")},
        )

    proofs = (await client.get("/delivery/recent-proofs", params={"limit": 5})).json()
    assert len(proofs) == 1
    image = await client.get(proofs[0]["url"])
    assert image.status_code == 200
    assert image.content == b"jpeg-bytes"


@pytest.mark.asyncio
async def test_exception_unknown_package_returns_404(int_client_driver):
    client, db, drv = int_client_driver

    resp = await client.post(
        "/delivery/exception",
        data={"package_id": "no-such-package", "driver_id": drv.id, "reason": "x"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_scan_loads_pending_package(int_client_driver):
    """Scanning a pending package marks it loaded and stamps loaded_at."""
    client, db, drv = int_client_driver
    pkg = await int_db_seed_package(db, status="pending")

    resp = await client.post("/delivery/scan", json={"barcode": pkg.id, "scan_type": "qr"})

    assert resp.status_code == 200
    assert resp.json()["package_status"] == "loaded"
    await db.refresh(pkg)
    assert pkg.status == "loaded"
    assert pkg.loaded_at is not None


@pytest.mark.asyncio
async def test_scan_by_tracking_code(int_client_driver):
    client, db, drv = int_client_driver
    pkg = await int_db_seed_package(db, status="pending")
    pkg.tracking_code = "TRK-123"
    await db.commit()

    resp = await client.post("/delivery/scan", json={"barcode": "TRK-123"})

    assert resp.status_code == 200
    assert resp.json()["package_id"] == pkg.id


@pytest.mark.asyncio
async def test_scan_does_not_undo_delivery(int_client_driver):
    """Rescanning a delivered package leaves it delivered."""
    client, db, drv = int_client_driver
    pkg = await int_db_seed_package(db, status="delivered")

    resp = await client.post("/delivery/scan", json={"barcode": pkg.id})

    assert resp.status_code == 200
    assert resp.json()["package_status"] == "delivered"


@pytest.mark.asyncio
async def test_scan_unknown_barcode_returns_404(int_client_driver):
    client, db, drv = int_client_driver

    resp = await client.post("/delivery/scan", json={"barcode": "nope"})
    assert resp.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", [
    ("get", "/delivery/recent-proofs"),
    ("get", "/delivery/proof/x.jpg"),
    ("post", "/delivery/scan"),
    ("post", "/delivery/confirm"),
    ("post", "/delivery/exception"),
    ("post", "/delivery/verify-location"),
])
async def test_delivery_endpoints_require_login(int_client_anon, method, path):
    client, db = int_client_anon

    resp = await getattr(client, method)(path)
    assert resp.status_code == 401
