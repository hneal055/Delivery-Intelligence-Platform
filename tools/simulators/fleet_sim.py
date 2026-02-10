import asyncio
import httpx
import random
import logging
import argparse
import time
from datetime import datetime
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("FleetSim")

API_BASE_URL = "http://127.0.0.1:8000"
DEVICE_API_KEY = "dev-secret-key-123"

CHICAGO_BOUNDS = {"lat_min": 41.8000, "lat_max": 42.0000, "lon_min": -87.8000, "lon_max": -87.6000}

class VirtualDriver:
    def __init__(self, driver_id: str):
        self.driver_id = driver_id
        self.client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0)
        self.current_location = self._random_location()
        self.stops: List[Dict] = []
        self.status = "IDLE"
        self.token = None

    def _random_location(self):
        return {
            "lat": random.uniform(CHICAGO_BOUNDS["lat_min"], CHICAGO_BOUNDS["lat_max"]),
            "lon": random.uniform(CHICAGO_BOUNDS["lon_min"], CHICAGO_BOUNDS["lon_max"]),
        }

    async def login(self):
        try:
            response = await self.client.post("/auth/token", data={
                "username": "driver1", "password": "driverpassword", "grant_type": "password"
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

        # Simulate movement
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
                    "timestamp": datetime.utcnow().isoformat(),
                    "speed": random.uniform(0, 60),
                    "heading": random.uniform(0, 360)
                },
                headers={"Authorization": f"Bearer {self.token}"}
            )
        except Exception as e:
            pass 

    async def perform_delivery(self):
        if not self.token: return
        
        # 10% Chance to deliver a package on this tick
        if random.random() > 0.1: 
            return

        pkg_id = f"PKG-{self.driver_id}-{int(time.time())}-{random.randint(1000,9999)}"
        
        # >1KB dummy image to pass verification
        dummy_image = b'x' * 2048 
        
        files = {'photo': ('proof.png', dummy_image, 'image/png')}
        data = {'package_id': pkg_id, 'driver_id': self.driver_id}
        
        try:
            logger.info(f"{self.driver_id} delivering {pkg_id}...")
            resp = await self.client.post(
                "/delivery/confirm",
                data=data,
                files=files,
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if resp.status_code != 200:
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
