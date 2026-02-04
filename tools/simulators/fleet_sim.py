import asyncio
import httpx
import random
import logging
import argparse
import time
from typing import List, Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("FleetSim")

API_BASE_URL = "http://127.0.0.1:8000"  # Changed from localhost
API_KEY = "dev-secret-key-123"

# Mock Data for simulation (Chicago, IL)
CHICAGO_BOUNDS = {
    "lat_min": 41.8000,
    "lat_max": 42.0000,
    "lon_min": -87.8000,
    "lon_max": -87.6000,
}


class VirtualDriver:
    def __init__(self, driver_id: str):
        self.driver_id = driver_id
        self.client = httpx.AsyncClient(
            base_url=API_BASE_URL, headers={"X-DIAD-Token": API_KEY}, timeout=10.0
        )
        self.current_location = self._random_location()
        self.stops: List[Dict] = []
        self.status = "IDLE"

    def _random_location(self):
        return {
            "lat": random.uniform(CHICAGO_BOUNDS["lat_min"], CHICAGO_BOUNDS["lat_max"]),
            "lon": random.uniform(CHICAGO_BOUNDS["lon_min"], CHICAGO_BOUNDS["lon_max"]),
        }

    async def get_route(self):
        """Request a route optimization from the backend."""
        logger.info(f"Driver {self.driver_id}: Requesting Route...")

        # Generate 3-5 random stops
        num_stops = random.randint(3, 5)
        raw_stops = [self._random_location() for _ in range(num_stops)]

        payload = {
            "driver_id": self.driver_id,
            "current_location": self.current_location,
            "stops": raw_stops,
        }

        try:
            response = await self.client.post("/route/optimize", json=payload)
            if response.status_code == 200:
                data = response.json()
                self.stops = data.get("optimized_stops", [])
                logger.info(
                    f"Driver {self.driver_id}: Received {len(self.stops)} optimized stops."
                )
                self.status = "DELIVERING"
            else:
                logger.error(
                    f"Driver {self.driver_id}: Failed to get route. {response.status_code}"
                )
        except Exception as e:
            logger.error(f"Driver {self.driver_id}: Connection Error: {e}")

    async def simulate_movement(self):
        """Simulate driving to the next stop."""
        if not self.stops:
            self.status = "IDLE"
            return

        target = self.stops[0]  # Next stop

        # Simple simulation: Teleport close to target with some noise
        # In a real sim, we would interpolate steps

        # 1. Move "near" the target (simulating arrival)
        logger.info(
            f"Driver {self.driver_id}: Driving to {target['lat']:.4f}, {target['lon']:.4f}..."
        )
        await asyncio.sleep(random.uniform(1, 3))  # Simulate driving time

        # Update location to be very close (within 10-60 meters)
        # Approx 0.0001 deg is ~11 meters
        lat_offset = random.uniform(-0.0005, 0.0005)
        lon_offset = random.uniform(-0.0005, 0.0005)

        self.current_location = {
            "lat": target["lat"] + lat_offset,
            "lon": target["lon"] + lon_offset,
        }

        # 2. Verify Location
        await self.verify_location(target)


    async def confirm_delivery(self, package_id: str):
        """Upload proof of delivery photo to finalize the job."""
        logger.info(f"Driver {self.driver_id}: Uploading Proof-of-Delivery photo for {package_id}...")
        
        # Create a dummy image (> 1KB to pass verifier)
        dummy_image = b"0" * 2048
        
        files = {
            "photo": ("pod_mock.jpg", dummy_image, "image/jpeg")
        }
        
        params = {
            "package_id": package_id,
            "driver_id": self.driver_id
        }

        try:
            # We use httpx to post multipart/form-data
            response = await self.client.post("/delivery/confirm", params=params, files=files)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Driver {self.driver_id}: DELIVERY CONFIRMED! Score: {data.get('verification_score')}")
            else:
                logger.error(f"Driver {self.driver_id}: Confirmation Failed: {response.text}")
                
        except Exception as e:
            logger.error(f"Driver {self.driver_id}: Upload Error: {e}")

    async def verify_location(self, target):
        """Ping API to check if we are close enough."""
        payload = {
            "driver_id": self.driver_id,
            "current_location": self.current_location,
            "target_delivery_location": target,
        }

        try:
            response = await self.client.post("/delivery/verify-location", json=payload)
            data = response.json()

            if data.get("allowed"):
                logger.info(
                    f"Driver {self.driver_id}: ARRIVED! Location verified. Delivering package."
                )
                # "Deliver" it
                self.stops.pop(0)
                await asyncio.sleep(1)  # Action time
            else:
                logger.warning(
                    f"Driver {self.driver_id}: Arrival Rejected. {data.get('message')}"
                )
                # Logic to 'move closer' could go here
                # For now, we force success next tick or just skip
                self.stops.pop(0)  # Skip to keep sim moving

        except Exception as e:
            logger.error(f"Driver {self.driver_id}: Verification Error: {e}")

    async def run_lifecycle(self):
        await self.get_route()
        while self.stops and self.status == "DELIVERING":
            await self.simulate_movement()

        logger.info(f"Driver {self.driver_id}: Shift Complete.")
        await self.client.aclose()


async def main():
    parser = argparse.ArgumentParser(description="Fleet Simulator")
    parser.add_argument(
        "--drivers", type=int, default=5, help="Number of virtual drivers"
    )
    args = parser.parse_args()

    num_drivers = args.drivers
    logger.info(f"Starting Fleet Simulation with {num_drivers} drivers in Chicago...")

    drivers = [VirtualDriver(f"driver-{i+1:03d}") for i in range(num_drivers)]

    # Run all drivers concurrently
    await asyncio.gather(*(d.run_lifecycle() for d in drivers))


if __name__ == "__main__":
    asyncio.run(main())
