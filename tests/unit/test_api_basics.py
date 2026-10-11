from fastapi.testclient import TestClient
from src.backend.api.main import app

client = TestClient(app)

# Device auth (X-DIAD-Token) is exercised through a real device-protected
# route; an empty stop list passes auth and then fails validation with 400.
OPTIMIZE_EMPTY = {
    "driver_id": "D001",
    "current_location": {"lat": 41.8781, "lon": -87.6298},
    "stops": [],
}


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_device_route_unauthorized():
    response = client.post("/routing/optimize", json=OPTIMIZE_EMPTY)
    assert response.status_code == 403


def test_device_route_authorized():
    response = client.post(
        "/routing/optimize",
        json=OPTIMIZE_EMPTY,
        headers={"X-DIAD-Token": "test-device-key"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "No stops provided"
