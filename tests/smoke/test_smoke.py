import os

import httpx

BASE_URL = os.getenv(
    "BACKEND_URL",
    "http://localhost:8000",
)


def test_backend_health():
    response = httpx.get(f"{BASE_URL}/health")
    assert response.status_code == 200


def test_auth_endpoint_available():
    response = httpx.post(
        f"{BASE_URL}/auth/token",
        data={
            "username": "nonexistent_user",
            "password": "badpassword",
            "grant_type": "password",
        },
    )

    assert response.status_code == 401

    body = response.json()

    assert "detail" in body