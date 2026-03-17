import pytest
import asyncio
import httpx
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("GeofenceTest")

API_BASE_URL = "http://localhost:8002"

@pytest.mark.skip(reason="manual smoke-test against live server; run with: python tests/test_geofencing.py")
async def test_geofencing():
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
        # 1. Login
        logger.info("1. Logging in...")
        resp = await client.post("/auth/token", data={
            "username": "driver1", "password": "driverpassword", "grant_type": "password"
        })
        if resp.status_code != 200:
            logger.error("Login failed")
            return
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Test Case: Success (0 meters distance)
        logger.info("\n2. Testing VALID location (0m distance)...")
        payload_valid = {
            "driver_id": "D001",
            "current_location": {"lat": 41.8781, "lon": -87.6298}, # Willis Tower
            "target_delivery_location": {"lat": 41.8781, "lon": -87.6298}
        }
        resp = await client.post("/delivery/verify-location", json=payload_valid, headers=headers)
        logger.info(f"Response: {resp.status_code} {resp.json()}")

        # 3. Test Case: Success (Inside 100m)
        # Roughly 1 degree lat = 111km -> 0.0001 deg ~ 11 meters
        logger.info("\n3. Testing VALID location (approx 11m distance)...")
        payload_near = {
            "driver_id": "D001",
            "current_location": {"lat": 41.8781, "lon": -87.6298},
            "target_delivery_location": {"lat": 41.8782, "lon": -87.6298} 
        }
        resp = await client.post("/delivery/verify-location", json=payload_near, headers=headers)
        logger.info(f"Response: {resp.status_code} {resp.json()}")

        # 4. Test Case: Failure (Outside Range)
        # 0.01 deg lat ~ 1.1km
        logger.info("\n4. Testing INVALID location (approx 1km distance)...")
        payload_far = {
            "driver_id": "D001",
            "current_location": {"lat": 41.8781, "lon": -87.6298},
            "target_delivery_location": {"lat": 41.8881, "lon": -87.6298}
        }
        resp = await client.post("/delivery/verify-location", json=payload_far, headers=headers)
        logger.info(f"Response: {resp.status_code} {resp.json()}")

if __name__ == "__main__":
    asyncio.run(test_geofencing())

