import pytest
from httpx import AsyncClient, ASGITransport
from src.backend.api.main import app

@pytest.mark.asyncio
async def test_optimize_route_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "driver_id": "driver-001",
            "current_location": {"lat": 40.7128, "lon": -74.0060}, # NYC City Hall
            "stops": [
                {"lat": 40.730610, "lon": -73.935242}, # Queens (East)
                {"lat": 34.0522, "lon": -118.2437},    # LA (Far West)
                {"lat": 40.7580, "lon": -73.9855}      # Times Sq (West of Queens)
            ]
        }

        headers = {"X-DIAD-Token": "dev-secret-key-123"}

        response = await client.post("/route/optimize", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_stops"] == 3

        optimized_stops = data["optimized_stops"]
        
        # Phase 9 Update: The 2-Opt Algorithm correctly identifies that going to Queens (East) 
        # THEN sweeping West to Times Sq and on to LA is more efficient than zig-zagging.
        # So we expect Queens (40.73061) to be first.
        assert optimized_stops[0]["lat"] == 40.730610

@pytest.mark.asyncio
async def test_optimize_route_empty():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "driver_id": "driver-001",
            "current_location": {"lat": 40.7128, "lon": -74.0060},
            "stops": []
        }
        headers = {"X-DIAD-Token": "dev-secret-key-123"}
        response = await client.post("/route/optimize", json=payload, headers=headers)
        assert response.status_code == 400
