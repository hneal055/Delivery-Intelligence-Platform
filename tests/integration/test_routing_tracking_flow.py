"""
Integration tests: Routing flow
- POST /route/optimize → haversine fallback (no Mapbox token in tests)
- POST /route/optimize with empty stops → 400
- GET  /tracking/live              → managers see live driver list
- POST /tracking/{driver_id}/location → updates driver position
- GET  /tracking/{driver_id}/history  → returns breadcrumb list
"""
import pytest
from unittest.mock import patch
from tests.integration.conftest import int_db_seed_driver
from src.backend.services.auth import get_current_device


# Override DIAD device auth for routing endpoints
def _authorized():
    return True


@pytest.mark.asyncio
async def test_route_optimize_haversine_fallback(int_client_driver):
    """POST /route/optimize returns sorted stops via haversine when Mapbox is off."""
    client, db, drv = int_client_driver

    # Override device-key auth used by routing.py
    from src.backend.api.main import app
    app.dependency_overrides[get_current_device] = _authorized

    resp = await client.post("/route/optimize", json={
        "driver_id": drv.id,
        "current_location": {"lat": 40.7128, "lon": -74.0060},
        "stops": [
            {"lat": 40.7589, "lon": -73.9851},
            {"lat": 40.6892, "lon": -74.0445},
            {"lat": 40.7282, "lon": -73.7949},
        ]
    })

    app.dependency_overrides.pop(get_current_device, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_stops"] == 3
    assert len(body["optimized_stops"]) == 3
    assert "haversine" in body["message"].lower() or "mapbox" in body["message"].lower()


@pytest.mark.asyncio
async def test_route_optimize_empty_stops_returns_400(int_client_driver):
    """POST /route/optimize with no stops returns 400."""
    client, db, drv = int_client_driver

    from src.backend.api.main import app
    app.dependency_overrides[get_current_device] = _authorized

    resp = await client.post("/route/optimize", json={
        "driver_id": drv.id,
        "current_location": {"lat": 40.7128, "lon": -74.0060},
        "stops": []
    })

    app.dependency_overrides.pop(get_current_device, None)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_update_driver_location(int_client_driver):
    """POST /tracking/{driver_id}/location stores GPS fix and records history."""
    client, db, drv = int_client_driver
    driver = await int_db_seed_driver(db, "GPS Driver")

    from datetime import datetime, timezone
    resp = await client.post(f"/tracking/{driver.id}/location", json={
        "lat": 40.7128,
        "lon": -74.0060,
        "speed": 30.5,
        "heading": 180.0,
        "battery_level": 0.85,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "updated"


@pytest.mark.asyncio
async def test_location_history_returns_list(int_client_driver):
    """GET /tracking/{driver_id}/history returns a list (possibly empty)."""
    client, db, drv = int_client_driver
    driver = await int_db_seed_driver(db, "History Driver")

    resp = await client.get(f"/tracking/{driver.id}/history")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_live_tracking_requires_manager(int_client_driver):
    """GET /tracking/live is forbidden for drivers (no VIEW_ALL_DRIVERS perm)."""
    client, db, drv = int_client_driver

    resp = await client.get("/tracking/live")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_live_tracking_manager_access(int_client_manager):
    """GET /tracking/live returns 200 for managers."""
    client, db, mgr = int_client_manager
    await int_db_seed_driver(db, "Active Driver")

    resp = await client.get("/tracking/live")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
