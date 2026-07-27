import asyncio
import base64
import httpx
import random
import logging
import argparse
import time
from datetime import datetime, timezone
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("FleetSim")

API_BASE_URL = "http://localhost:8002"
DEVICE_API_KEY = "dev-secret-key-123"

CHICAGO_BOUNDS = {"lat_min": 41.8000, "lat_max": 42.0000, "lon_min": -87.8000, "lon_max": -87.6500}
# NOTE: This is a rectangular approximation of the service area. Chicago's
# actual shoreline runs diagonally, so a box reaching all the way to the true
# eastern edge of the city (~-87.60) includes a large amount of open Lake
# Michigan. -87.65 stays reliably over land at the cost of excluding the
# immediate lakefront strip. A proper fix would check candidate points
# against a real land polygon instead of a bounding rectangle.

# How close (in degrees, ~0.0002 deg ~= 22m) a driver must be to its assigned
# stop before a delivery is attempted. Small enough to reliably satisfy the
# backend's geofence check, large enough that the driver has genuinely
# traveled there rather than teleporting.
ARRIVAL_THRESHOLD_DEG = 0.0002

class VirtualDriver:
    def __init__(self, driver_id: str):
        self.driver_id = driver_id
        self.client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0)
        self.current_location = self._random_location()
        self.stops: List[Dict] = []
        self.status = "IDLE"
        self.token = None
        self._assign_new_stop()

    def _random_location(self):
        return {
            "lat": random.uniform(CHICAGO_BOUNDS["lat_min"], CHICAGO_BOUNDS["lat_max"]),
            "lon": random.uniform(CHICAGO_BOUNDS["lon_min"], CHICAGO_BOUNDS["lon_max"]),
        }

    def _assign_new_stop(self):
        """Pick a genuinely new destination somewhere in the service area.
        This is a REAL destination the driver will spend multiple ticks
        actually traveling toward -- not a point fabricated next to its
        current position."""
        dest = self._random_location()
        self.stops = [{"dest_lat": dest["lat"], "dest_lon": dest["lon"]}]

    async def login(self):
        try:
            username = f"driver{int(self.driver_id[1:])}"
            response = await self.client.post("/auth/token", data={
                "username": username, "password": "driverpassword", "grant_type": "password"
            })
            if response.status_code == 200:
                self.token = response.json()["access_token"]
            else:
                logger.error(f"Login Failed: {response.text}")
        except Exception as e:
            logger.error(f"Login connection error: {e}")

    async def update_location(self):
        if not self.token:
            return

        # Move toward the assigned stop (closes 10% of the remaining
        # distance per tick -- an asymptotic approach that takes several
        # minutes for a realistic cross-city trip, similar to a real route).
        if self.stops:
            target = self.stops[0]
            lat_diff = target["dest_lat"] - self.current_location["lat"]
            lon_diff = target["dest_lon"] - self.current_location["lon"]
            self.current_location["lat"] += lat_diff * 0.1
            self.current_location["lon"] += lon_diff * 0.1
        else:
            self.current_location["lat"] += random.uniform(-0.001, 0.001)
            self.current_location["lon"] += random.uniform(-0.001, 0.001)

        try:
            await self.client.post(
                f"/tracking/{self.driver_id}/location",
                json={
                    "lat": self.current_location["lat"],
                    "lon": self.current_location["lon"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "speed": random.uniform(0, 60),
                    "heading": random.uniform(0, 360)
                },
                headers={"Authorization": f"Bearer {self.token}"}
            )
        except Exception as e:
            pass

    async def perform_delivery(self):
        if not self.token or not self.stops:
            return

        target = self.stops[0]

        # Only attempt a delivery once we've actually arrived at the
        # assigned stop -- not on a random per-tick chance regardless of
        # position.
        lat_gap = abs(target["dest_lat"] - self.current_location["lat"])
        lon_gap = abs(target["dest_lon"] - self.current_location["lon"])
        if lat_gap > ARRIVAL_THRESHOLD_DEG or lon_gap > ARRIVAL_THRESHOLD_DEG:
            return

        # 1. VERIFY LOCATION (Geofencing Check) -- against the REAL stop,
        # not a fabricated nearby point.
        try:
            verify_payload = {
                "driver_id": self.driver_id,
                "current_location": self.current_location,
                "target_delivery_location": {"lat": target["dest_lat"], "lon": target["dest_lon"]}
            }
            verify_resp = await self.client.post(
                "/delivery/verify-location",
                json=verify_payload,
                headers={"Authorization": f"Bearer {self.token}"}
            )

            if verify_resp.status_code == 200:
                result = verify_resp.json()
                if not result.get("allowed"):
                    logger.warning(f"{self.driver_id} Geofence Blocked: {result.get('message')}")
                    return
            else:
                logger.warning(f"Geofence Check Failed: {verify_resp.status_code}")
        except Exception as e:
            logger.error(f"Geofence Error: {e}")
            return

        # 2. PERFORM DELIVERY
        pkg_id = f"PKG-{self.driver_id}-{int(time.time())}-{random.randint(1000,9999)}"

        with open('tools/simulators/dummy_proof.jpg', 'rb') as f:
            dummy_image = f.read()

        files = {"photo": ("proof.jpg", dummy_image, "image/jpeg")}
        data = {
            "package_id": pkg_id,
            "driver_id": self.driver_id,
            "dest_lat": target["dest_lat"],
            "dest_lon": target["dest_lon"],
        }

        try:
            logger.info(f"{self.driver_id} delivering {pkg_id}...")
            resp = await self.client.post(
                "/delivery/confirm",
                data=data,
                files=files,
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if resp.status_code == 200:
                # Delivery complete -- head to a brand new, realistically
                # distant destination next.
                self._assign_new_stop()
            else:
                logger.warning(f"Delivery failed: {resp.text}")
        except Exception as e:
            logger.error(f"Delivery Exception: {e}")

    async def run(self):
        await self.login()
        while True:
            await self.update_location()
            await self.perform_delivery()
            await asyncio.sleep(5)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--drivers", type=int, default=10)
    args = parser.parse_args()

    logger.info(f"Starting Fleet Simulation with {args.drivers} drivers...")

    drivers = [VirtualDriver(f"D{i+1:03d}") for i in range(args.drivers)]

    # Run all drivers concurrently
    await asyncio.gather(*[d.run() for d in drivers])

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopping simulation...")
