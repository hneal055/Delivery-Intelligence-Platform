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

    with patch("src.backend.api.routes.dispatch.geocode_in_service_area", AsyncMock(return_value=MART)):
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

    with patch("src.backend.api.routes.dispatch.geocode_in_service_area", AsyncMock(return_value=None)):
        resp = await client.post("/dispatch/jobs", json={"title": "X", "dest_address": "nowhere at all"})

    assert resp.status_code == 422
    assert "Address not found" in resp.json()["detail"]
    assert (await db.execute(select(PackageSQL))).scalars().all() == []


@pytest.mark.asyncio
async def test_create_job_rejects_unknown_driver_or_package(int_client_manager):
    client, db, mgr = int_client_manager

    assert (await client.post("/dispatch/jobs", json={"title": "X", "driver_id": "ghost"})).status_code == 404
    assert (await client.post("/dispatch/jobs", json={"title": "X", "package_id": "ghost"})).status_code == 404


@pytest.mark.asyncio
async def test_unit_and_instructions_reach_the_driver(int_client_manager):
    """Suite/floor and delivery instructions are stored on the package and
    returned with it (the driver's phone reads /dispatch/deliveries)."""
    client, db, mgr = int_client_manager
    driver = await int_db_seed_driver(db, "Van")

    with patch("src.backend.api.routes.dispatch.geocode_in_service_area", AsyncMock(return_value=MART)):
        job = (await client.post("/dispatch/jobs", json={
            "title": "Concierge drop",
            "driver_id": driver.id,
            "dest_address": "111 west wacker",
            "dest_unit": "Suite 2000, 20th floor",
            "delivery_instructions": "Leave with concierge",
        })).json()

    pkgs = (await client.get("/dispatch/packages")).json()
    pkg = next(p for p in pkgs if p["id"] == job["package_id"])
    assert pkg["dest_unit"] == "Suite 2000, 20th floor"
    assert pkg["delivery_instructions"] == "Leave with concierge"


@pytest.mark.asyncio
async def test_geocode_preview(int_client_manager):
    client, db, mgr = int_client_manager
    hit = GeocodeResult(lat=41.886, lon=-87.634, matched_address="111 W WACKER DR, CHICAGO, IL, 60601",
                        used_default_area=True)

    with patch("src.backend.api.routes.dispatch.geocode_in_service_area", AsyncMock(return_value=hit)):
        ok = await client.get("/dispatch/geocode", params={"address": "111 west wacker"})
    with patch("src.backend.api.routes.dispatch.geocode_in_service_area", AsyncMock(return_value=None)):
        miss = await client.get("/dispatch/geocode", params={"address": "nowhere"})

    assert ok.status_code == 200
    assert ok.json()["matched_address"].startswith("111 W WACKER")
    assert ok.json()["used_default_area"] is True
    assert miss.status_code == 404


async def _seed_driver_account(db, username):
    """A driver login account plus its driver profile (id = username)."""
    from tests.integration.conftest import int_db_seed_user
    from src.backend.models.domain import UserRole as _Role
    from src.backend.models.sql_models import Driver as _Driver
    user = await int_db_seed_user(db, username, "Password1!", _Role.DRIVER)
    db.add(_Driver(id=username, name=username, status="active"))
    await db.commit()
    return user


@pytest.mark.asyncio
async def test_pickup_job_not_ready_then_marked_ready_alerts_driver(int_client_manager):
    """Pickup -> delivery job: pickup geocoded, 'not ready' until dispatch marks
    it ready; the driver's phone is pushed on assignment and on ready."""
    from src.backend.models.sql_models import DeviceToken
    client, db, mgr = int_client_manager
    user = await _seed_driver_account(db, "van1")
    db.add(DeviceToken(user_id=user.id, token="ExponentPushToken[van1]", platform="ios"))
    await db.commit()

    pickup = GeocodeResult(lat=41.9, lon=-87.7, matched_address="2500 W ARMITAGE AVE, CHICAGO, IL, 60647")
    sent = AsyncMock(return_value={"status": "ok"})
    with patch("src.backend.api.routes.dispatch.geocode_in_service_area",
               AsyncMock(side_effect=[MART, pickup])), \
         patch("src.backend.services.driver_alerts.send_push_notification", sent):
        job = (await client.post("/dispatch/jobs", json={
            "title": "Parts run", "driver_id": "van1",
            "dest_address": "222 W Merchandise Mart Plaza",
            "pickup_address": "2500 W Armitage Ave",
            "pickup_instructions": "Ask for Luis at the parts counter",
            "ready_for_pickup": False,
        })).json()

        pkg = next(p for p in (await client.get("/dispatch/packages")).json() if p["id"] == job["package_id"])
        assert pkg["pickup_address"].startswith("2500 W ARMITAGE")
        assert pkg["pickup_instructions"] == "Ask for Luis at the parts counter"
        assert pkg["ready_at"] is None
        assert pkg["tracking_code"].startswith("CCC-")

        ready = await client.put(f"/dispatch/packages/{job['package_id']}/ready")
        assert ready.status_code == 200

    kinds = [c.args[3]["kind"] for c in sent.call_args_list]
    assert kinds == ["assigned", "ready"]
    assert all(c.args[0] == "ExponentPushToken[van1]" for c in sent.call_args_list)
    assert sent.call_args_list[0].args[1] == "New pickup & delivery"


@pytest.mark.asyncio
async def test_unknown_pickup_address_is_rejected(int_client_manager):
    client, db, mgr = int_client_manager
    with patch("src.backend.api.routes.dispatch.geocode_in_service_area",
               AsyncMock(side_effect=[MART, None])):
        resp = await client.post("/dispatch/jobs", json={
            "title": "X", "dest_address": "222 W Merchandise Mart Plaza", "pickup_address": "nowhere",
        })
    assert resp.status_code == 422
    assert "Pickup address not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_reopen_only_packages_with_a_problem(int_client_manager):
    client, db, mgr = int_client_manager
    bad = await int_db_seed_package(db, driver_id=None, status="exception")
    bad.exception_reason = "Business closed"
    ok = await int_db_seed_package(db, status="assigned")
    await db.commit()

    resp = await client.put(f"/dispatch/packages/{bad.id}/reopen")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
    await db.refresh(bad)
    assert bad.exception_reason is None
    assert (await client.put(f"/dispatch/packages/{ok.id}/reopen")).status_code == 409


@pytest.mark.asyncio
async def test_reopen_after_pickup_returns_to_delivery_stage(int_client_manager):
    """A problem reported after pickup (package in the van) reopens as loaded,
    not back at the pickup stage."""
    from datetime import datetime, timezone
    client, db, mgr = int_client_manager
    pkg = await int_db_seed_package(db, driver_id="van1", status="exception")
    pkg.loaded_at = datetime.now(timezone.utc)
    await db.commit()

    resp = await client.put(f"/dispatch/packages/{pkg.id}/reopen")
    assert resp.json()["status"] == "loaded"


@pytest.mark.asyncio
async def test_pickup_job_needs_pickup_address(int_client_manager):
    client, db, mgr = int_client_manager
    pickup = GeocodeResult(lat=41.9, lon=-87.7, matched_address="2500 W ARMITAGE AVE, CHICAGO, IL, 60647")

    missing = await client.post("/dispatch/jobs", json={
        "title": "P", "type": "pickup", "dest_address": "222 W Merchandise Mart Plaza",
    })
    with patch("src.backend.api.routes.dispatch.geocode_in_service_area",
               AsyncMock(side_effect=[MART, pickup])):
        ok = await client.post("/dispatch/jobs", json={
            "title": "P", "type": "pickup", "dest_address": "222 W Merchandise Mart Plaza",
            "pickup_address": "2500 W Armitage Ave",
        })

    assert missing.status_code == 422
    assert ok.status_code == 200 and ok.json()["type"] == "pickup"


@pytest.mark.asyncio
async def test_recipient_and_pickup_contact_reach_the_driver(int_client_manager):
    client, db, mgr = int_client_manager
    pickup = GeocodeResult(lat=41.9, lon=-87.7, matched_address="2500 W ARMITAGE AVE, CHICAGO, IL, 60647")
    with patch("src.backend.api.routes.dispatch.geocode_in_service_area",
               AsyncMock(side_effect=[MART, pickup])):
        job = (await client.post("/dispatch/jobs", json={
            "title": "Contacts", "dest_address": "222 W Merchandise Mart Plaza",
            "recipient_name": "Maria Lopez", "recipient_phone": "312-555-0142",
            "pickup_address": "2500 W Armitage Ave",
            "pickup_contact_name": "Luis", "pickup_contact_phone": "(773) 555-0199",
        })).json()

    pkg = next(p for p in (await client.get("/dispatch/packages")).json() if p["id"] == job["package_id"])
    assert (pkg["recipient_name"], pkg["recipient_phone"]) == ("Maria Lopez", "312-555-0142")
    assert (pkg["pickup_contact_name"], pkg["pickup_contact_phone"]) == ("Luis", "(773) 555-0199")


# --- deliver-by -----------------------------------------------------------------

from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_create_job_with_deliver_by(int_client_manager):
    """The promised time is stored on the package and returned with it."""
    client, db, mgr = int_client_manager
    promised = (datetime.now(timezone.utc) + timedelta(hours=3)).replace(microsecond=0)

    with patch("src.backend.api.routes.dispatch.geocode_in_service_area", AsyncMock(return_value=MART)):
        resp = await client.post("/dispatch/jobs", json={
            "title": "Lunch-hour parts", "type": "delivery",
            "dest_address": "222 W Merchandise Mart Plaza", "deliver_by": promised.isoformat(),
        })
    assert resp.status_code == 200
    pkg = (await db.execute(select(PackageSQL).where(PackageSQL.id == resp.json()["package_id"]))).scalar_one()
    stored = pkg.deliver_by if pkg.deliver_by.tzinfo else pkg.deliver_by.replace(tzinfo=timezone.utc)
    assert stored == promised

    listed = (await client.get("/dispatch/packages")).json()
    mine = next(p for p in listed if p["id"] == pkg.id)
    assert mine["deliver_by"] is not None


@pytest.mark.asyncio
async def test_create_job_with_past_deliver_by_rejected(int_client_manager):
    client, db, mgr = int_client_manager
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    with patch("src.backend.api.routes.dispatch.geocode_in_service_area", AsyncMock(return_value=MART)):
        resp = await client.post("/dispatch/jobs", json={
            "title": "Too late", "type": "delivery",
            "dest_address": "222 W Merchandise Mart Plaza", "deliver_by": past.isoformat(),
        })
    assert resp.status_code == 422
    assert "past" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_dashboard_on_time_rate(int_client_manager):
    """On time = proof captured no later than deliver_by (last 7 days)."""
    from src.backend.models.sql_models import DeliveryProof
    client, db, mgr = int_client_manager
    now = datetime.now(timezone.utc)
    for i, (promised_offset, delivered_offset) in enumerate([(60, 30), (60, 90), (60, 10)]):
        p = await int_db_seed_package(db, status="delivered")
        p.deliver_by = now - timedelta(minutes=200) + timedelta(minutes=promised_offset)
        db.add(DeliveryProof(
            package_id=p.id, driver_id="driver1", photo_key=f"ot-{i}.jpg",
            captured_at=now - timedelta(minutes=200) + timedelta(minutes=delivered_offset),
        ))
    await db.commit()

    body = (await client.get("/dispatch/dashboard/summary")).json()
    assert body["on_time_total"] == 3
    assert body["on_time_delivered"] == 2
