import pytest
from fastapi.testclient import TestClient
from src.backend.api.main import app
from src.backend.core.config import settings

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def normal_user_token_headers(client):
    login_data = {
        "username": "driver1",
        "password": "driverpassword",
        "grant_type": "password"
    }
    r = client.post("/auth/token", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {a_token}"}
    return headers

