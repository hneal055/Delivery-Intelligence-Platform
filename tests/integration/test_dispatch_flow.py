"""
Integration tests: Dispatch flow
- POST /dispatch/jobs        → creates job, returns id
- GET  /dispatch/jobs/{id}   → retrieves the job
- GET  /dispatch/jobs        → list all jobs, optionally filtered by status
- PUT  /dispatch/jobs/{id}/assign?driver_id=... → sets driver_id, status=assigned
- GET  /dispatch/dashboard/summary → counts drivers and packages
- GET  /dispatch/drivers           → lists drivers
"""
import pytest
from tests.integration.conftest import int_db_seed_driver, int_db_seed_package


@pytest.mark.asyncio
async def test_create_job(int_client_manager):
    """POST /dispatch/jobs returns the created job with an ID."""
    client, db, mgr = int_client_manager

    resp = await client.post("/dispatch/jobs", json={
        "title": "Morning Route A",
        "type": "delivery",
        "priority": "high",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Morning Route A"
    assert "id" in body
    assert body["status"] == "pending"


@pytest.mark.asyncio
async def test_get_job_by_id(int_client_manager):
    """GET /dispatch/jobs/{id} retrieves the exact job."""
    client, db, mgr = int_client_manager

    create_resp = await client.post("/dispatch/jobs", json={"title": "Route B", "type": "delivery"})
    job_id = create_resp.json()["id"]

    get_resp = await client.get(f"/dispatch/jobs/{job_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == job_id
    assert get_resp.json()["title"] == "Route B"


@pytest.mark.asyncio
async def test_list_jobs(int_client_manager):
    """GET /dispatch/jobs returns all created jobs."""
    client, db, mgr = int_client_manager

    await client.post("/dispatch/jobs", json={"title": "Job 1", "type": "delivery"})
    await client.post("/dispatch/jobs", json={"title": "Job 2", "type": "pickup"})

    resp = await client.get("/dispatch/jobs")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_assign_job_to_driver(int_client_manager):
    """PUT /dispatch/jobs/{id}/assign sets driver and status=assigned."""
    client, db, mgr = int_client_manager
    driver = await int_db_seed_driver(db, "Delivery Driver 1")

    create_resp = await client.post("/dispatch/jobs", json={"title": "Assign Me", "type": "delivery"})
    job_id = create_resp.json()["id"]

    assign_resp = await client.put(
        f"/dispatch/jobs/{job_id}/assign",
        params={"driver_id": driver.id},
    )
    assert assign_resp.status_code == 200
    body = assign_resp.json()
    assert body["driver_id"] == driver.id
    assert body["status"] == "assigned"


@pytest.mark.asyncio
async def test_assign_job_unknown_driver(int_client_manager):
    """Assigning to a non-existent driver_id returns 404."""
    client, db, mgr = int_client_manager

    create_resp = await client.post("/dispatch/jobs", json={"title": "Fail Job", "type": "delivery"})
    job_id = create_resp.json()["id"]

    resp = await client.put(
        f"/dispatch/jobs/{job_id}/assign",
        params={"driver_id": "nonexistent-driver-id"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Driver not found"


@pytest.mark.asyncio
async def test_assign_unknown_job(int_client_manager):
    """Assigning a non-existent job returns 404."""
    client, db, mgr = int_client_manager
    driver = await int_db_seed_driver(db)

    resp = await client.put(
        "/dispatch/jobs/does-not-exist/assign",
        params={"driver_id": driver.id},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_jobs_filter_by_status(int_client_manager):
    """GET /dispatch/jobs?status=pending returns only pending jobs."""
    client, db, mgr = int_client_manager

    cr = await client.post("/dispatch/jobs", json={"title": "Pending Job", "type": "delivery"})
    assert cr.json()["status"] == "pending"

    resp = await client.get("/dispatch/jobs", params={"status": "pending"})
    assert resp.status_code == 200
    jobs = resp.json()
    assert all(j["status"] == "pending" for j in jobs)


@pytest.mark.asyncio
async def test_dashboard_summary(int_client_manager):
    """GET /dispatch/dashboard/summary returns correct driver/package counts."""
    client, db, mgr = int_client_manager
    await int_db_seed_driver(db, "Driver Alpha")
    await int_db_seed_package(db)

    resp = await client.get("/dispatch/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_drivers"] >= 1
    assert body["total_packages"] >= 1


@pytest.mark.asyncio
async def test_list_drivers(int_client_manager):
    """GET /dispatch/drivers returns at least the seeded driver."""
    client, db, mgr = int_client_manager
    await int_db_seed_driver(db, "Driver Beta")

    resp = await client.get("/dispatch/drivers")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_assign_job_assigns_its_package(int_client_manager):
    """Assigning a job puts its package on the driver's manifest."""
    client, db, mgr = int_client_manager
    driver = await int_db_seed_driver(db, "Van Driver")
    pkg = await int_db_seed_package(db, status="pending")

    create_resp = await client.post(
        "/dispatch/jobs", json={"title": "Drop", "type": "delivery", "package_id": pkg.id}
    )
    job_id = create_resp.json()["id"]
    resp = await client.put(f"/dispatch/jobs/{job_id}/assign", params={"driver_id": driver.id})

    assert resp.status_code == 200
    await db.refresh(pkg)
    assert pkg.driver_id == driver.id
    assert pkg.status == "assigned"


@pytest.mark.asyncio
async def test_driver_sees_only_own_deliveries(int_client_driver):
    """A driver's /dispatch/deliveries is limited to packages assigned to them,
    even if they ask for another driver's."""
    client, db, drv = int_client_driver
    mine = await int_db_seed_driver(db, "mine")
    mine.id = drv.username  # driver ID == login username
    other = await int_db_seed_driver(db, "other")
    await db.commit()
    own_pkg = await int_db_seed_package(db, driver_id=drv.username)
    await int_db_seed_package(db, driver_id=other.id)

    for params in ({}, {"driver_id": other.id}):
        resp = await client.get("/dispatch/deliveries", params=params)
        assert resp.status_code == 200
        assert [p["id"] for p in resp.json()] == [own_pkg.id]


@pytest.mark.asyncio
async def test_update_job_status(int_client_manager):
    client, db, mgr = int_client_manager
    job_id = (await client.post("/dispatch/jobs", json={"title": "S"})).json()["id"]

    resp = await client.put(f"/dispatch/jobs/{job_id}/status", params={"status": "completed"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["completed_at"] is not None

    bad = await client.put(f"/dispatch/jobs/{job_id}/status", params={"status": "bogus"})
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_delete_job_keeps_completed(int_client_manager):
    client, db, mgr = int_client_manager
    open_id = (await client.post("/dispatch/jobs", json={"title": "A"})).json()["id"]
    done_id = (await client.post("/dispatch/jobs", json={"title": "B"})).json()["id"]
    await client.put(f"/dispatch/jobs/{done_id}/status", params={"status": "completed"})

    assert (await client.delete(f"/dispatch/jobs/{open_id}")).status_code == 204
    assert (await client.get(f"/dispatch/jobs/{open_id}")).status_code == 404
    assert (await client.delete(f"/dispatch/jobs/{done_id}")).status_code == 409
    assert (await client.delete("/dispatch/jobs/nope")).status_code == 404


@pytest.mark.asyncio
async def test_availability_set_and_list(int_client_manager):
    client, db, mgr = int_client_manager
    driver = await int_db_seed_driver(db)

    created = await client.post("/dispatch/availability", json={
        "driver_id": driver.id, "date": "2026-10-12T00:00:00Z",
        "is_available": True, "start_time": "08:00", "end_time": "16:00",
    })
    assert created.status_code == 200
    assert created.json()["driver_id"] == driver.id

    resp = await client.get("/dispatch/availability", params={
        "start_date": "2026-10-11T00:00:00Z", "end_date": "2026-10-13T00:00:00Z",
    })
    assert resp.status_code == 200
    assert [a["start_time"] for a in resp.json()] == ["08:00"]


from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from src.backend.models.sql_models import Package as PackageSQL
from src.backend.services.geocoding import GeocodeResult

MART = GeocodeResult(lat=41.888, lon=-87.634, matched_address="222 W MERCHANDISE MART PLZ, CHICAGO, IL, 60654")


@pytest.mark.asyncio
async def test_create_delivery_job_from_address(int_client_manager):
    """A delivery job with an address creates a geocoded package on the driver's manifest."""
    client, db, mgr = int_client_manager
    driver = await int_db_seed_driver(db, "Van")

    with patch("src.backend.api.routes.dispatch.geocode_address", AsyncMock(return_value=MART)):
        resp = await client.post("/dispatch/jobs", json={
            "title": "Emergency construction parts",
            "type": "delivery",
            "driver_id": driver.id,
            "dest_address": "222 W Merchandise Mart Plaza, Chicago, IL",
        })

    assert resp.status_code == 200
    job = resp.json()
    assert job["status"] == "assigned"
    pkg = (await db.execute(select(PackageSQL).where(PackageSQL.id == job["package_id"]))).scalar_one()
    assert pkg.dest_address == MART.matched_address
    assert (pkg.dest_lat, pkg.dest_lon) == (MART.lat, MART.lon)
    assert pkg.driver_id == driver.id
    assert pkg.status == "assigned"
    assert pkg.tracking_code.startswith("CCC-")


@pytest.mark.asyncio
async def test_create_job_unknown_address_is_rejected(int_client_manager):
    client, db, mgr = int_client_manager

    with patch("src.backend.api.routes.dispatch.geocode_address", AsyncMock(return_value=None)):
        resp = await client.post("/dispatch/jobs", json={"title": "X", "dest_address": "nowhere at all"})

    assert resp.status_code == 422
    assert "Address not found" in resp.json()["detail"]
    assert (await db.execute(select(PackageSQL))).scalars().all() == []


@pytest.mark.asyncio
async def test_create_job_rejects_unknown_driver_or_package(int_client_manager):
    client, db, mgr = int_client_manager

    assert (await client.post("/dispatch/jobs", json={"title": "X", "driver_id": "ghost"})).status_code == 404
    assert (await client.post("/dispatch/jobs", json={"title": "X", "package_id": "ghost"})).status_code == 404
