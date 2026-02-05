import asyncio
import httpx
import random
import logging
import argparse
import time
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
        except Exception:
            pass

    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @property
    def device_headers(self):
        return {"X-DIAD-Token": DEVICE_API_KEY}


    async def get_route(self):
        logger.info(f"Driver {self.driver_id}: Requesting Route...")
        num_stops = random.randint(3, 5)
        raw_stops = [self._random_location() for _ in range(num_stops)]
        payload = {"driver_id": self.driver_id, "current_location": self.current_location, "stops": raw_stops}

        try:
            response = await self.client.post("/route/optimize", json=payload, headers=self.device_headers)
            if response.status_code == 200:
                self.stops = response.json().get("optimized_stops", [])
                self.status = "DELIVERING"
        except Exception:
            pass

    async def predict_eta(self, target_node):
        dist = ((target_node["lat"] - self.current_location["lat"])**2 + 
                (target_node["lon"] - self.current_location["lon"])**2)**0.5 * 111.0
        payload = {"distance_km": max(0.1, dist), "traffic_load": random.random(), "num_packages": 1}
        try:
            await self.client.post("/analytics/predict-eta", json=payload, headers=self.auth_headers)
        except Exception:
            pass


    async def simulate_movement(self):
        if not self.stops:
            self.status = "IDLE"
            return
        target = self.stops[0]
        await self.predict_eta(target)
        await asyncio.sleep(random.uniform(0.5, 2.0))
        self.current_location = {"lat": target["lat"] + 0.0001, "lon": target["lon"] + 0.0001}
        await self.verify_location(target)

    async def confirm_delivery(self, package_id: str):
        dummy_image = b"0" * 2048
        files = {"photo": ("pod_mock.jpg", dummy_image, "image/jpeg")}
        try:
            resp = await self.client.post("/delivery/confirm", data={"package_id": package_id, "driver_id": self.driver_id}, files=files, headers=self.auth_headers)
            if resp.status_code == 200:
                logger.info(f"Driver {self.driver_id}: Delivered {package_id}")
        except Exception:
            pass

    async def verify_location(self, target):
        payload = {"driver_id": self.driver_id, "current_location": self.current_location, "target_delivery_location": target}
        try:
            response = await self.client.post("/delivery/verify-location", json=payload, headers=self.auth_headers)
            if response.json().get("allowed"):
                self.stops.pop(0)
                await self.confirm_delivery(f"PKG-{self.driver_id}-{int(time.time())}")
            else:
                self.stops.pop(0)
        except Exception:
            self.stops.pop(0)

    async def run_lifecycle(self):
        await self.login()
        if not self.token: return
        while True:
            await self.get_route()
            while self.stops and self.status == "DELIVERING":
                await self.simulate_movement()
            await asyncio.sleep(random.uniform(2.0, 5.0))

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--drivers", type=int, default=5)
    args = parser.parse_args()
    logger.info(f"Starting Fleet Simulation with {args.drivers} drivers...")
    drivers = [VirtualDriver(f"D{i+1:03d}") for i in range(args.drivers)]
    await asyncio.gather(*(d.run_lifecycle() for d in drivers))

if __name__ == "__main__":
    asyncio.run(main())
