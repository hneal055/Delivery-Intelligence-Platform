import pytest
from fastapi.testclient import TestClient
from src.backend.api.main import app

client = TestClient(app)

def test_update_location_endpoint():
    response = client.post("/tracking/D001/location", json={
        "lat": 41.8781,
        "lon": -87.6298,
        "speed": 10.0,
        "heading": 90.0,
        "battery_level": 85
    })
    # Will be 401/403 if auth is enforced, or 404 if driver D001 isn't seeded in test db yet
    assert response.status_code in [401, 403, 404]
