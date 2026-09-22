import os
import sys
import asyncio
import random
import httpx

DEVICE_API_KEY = os.getenv("DIAD_API_KEY")
DRIVER_PASSWORD = os.getenv("DRIVER_PASSWORD")
BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8002")

if not DEVICE_API_KEY:
    print("ERROR: DIAD_API_KEY environment variable is required for the simulator.", file=sys.stderr)
    sys.exit(1)

if not DRIVER_PASSWORD:
    print("ERROR: DRIVER_PASSWORD environment variable is required for the simulator.", file=sys.stderr)
    sys.exit(1)

class FleetSimulator:
    def __init__(self, base_url: str, username: str, driver_id: str):
        self.base_url = base_url
        self.username = username
        self.driver_id = driver_id
        self.token = None

    async def authenticate(self):
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.post("/auth/token", data={
                "username": self.username, 
                "password": DRIVER_PASSWORD, 
                "grant_type": "password"
            })
            if response.status_code == 200:
                self.token = response.json().get("access_token")
            else:
                print(f"Authentication failed for {self.username}: {response.text}", file=sys.stderr)
                sys.exit(1)

    async def simulate(self):
        await self.authenticate()
        print(f"Simulator started for {self.username} (ID: {self.driver_id})")
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            while True:
                lat = 41.8781 + random.uniform(-0.02, 0.02)
                lng = -87.6298 + random.uniform(-0.02, 0.02)
                headers = {"Authorization": f"Bearer {self.token}", "X-DIAD-Token": DEVICE_API_KEY}
                try:
                    endpoint = f"/tracking/{self.driver_id}/location"
                    response = await client.post(endpoint, json={
                        "lat": lat,
                        "lon": lng,
                        "speed": random.uniform(0, 45),
                        "heading": random.uniform(0, 360),
                        "battery_level": random.randint(50, 100)
                    }, headers=headers)
                    if response.status_code == 200:
                        print(f"[{self.username}] Sent telemetry to {endpoint}: {lat:.4f}, {lng:.4f}")
                    else:
                        print(f"[{self.username}] Telemetry error ({endpoint}): {response.status_code} - {response.text}")
                except Exception as e:
                    print(f"[{self.username}] Connection error: {e}")
                await asyncio.sleep(5)

async def main():
    tasks = [
        FleetSimulator(BASE_URL, f"driver{i}", f"D{i:03d}").simulate() 
        for i in range(1, 6)
    ]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
