from fastapi.testclient import TestClient
from src.backend.api.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "online"}

def test_secure_ping_unauthorized():
    response = client.post("/secure-ping")
    assert response.status_code == 403

def test_secure_ping_authorized():
    response = client.post(
        "/secure-ping",
        headers={"X-DIAD-Token": "dev-secret-key-123"}
    )
    assert response.status_code == 200
    assert response.json() == {"msg": "Device Authenticated"}
