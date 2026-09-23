import pytest
import httpx
import os

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8002")

def test_backend_health():
    response = httpx.get(f"{BASE_URL}/docs")
    assert response.status_code == 200

def test_auth_flow():
    response = httpx.post(f"{BASE_URL}/auth/token", data={
        "username": "admin",
        "password": "adminpassword",
        "grant_type": "password"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
