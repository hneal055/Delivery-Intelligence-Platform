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
    """Assigning to a non-existent driver_id returns 400."""
    client, db, mgr = int_client_manager

    create_resp = await client.post("/dispatch/jobs", json={"title": "Fail Job", "type": "delivery"})
    job_id = create_resp.json()["id"]

    resp = await client.put(
        f"/dispatch/jobs/{job_id}/assign",
        params={"driver_id": "nonexistent-driver-id"},
    )
    assert resp.status_code == 400


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
