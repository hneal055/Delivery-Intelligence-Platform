import asyncio
import os
import random
import sys
import httpx

DRIVER_PASSWORD = os.getenv("DRIVER_PASSWORD")
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "default-device-key")

if not DRIVER_PASSWORD:
    print("ERROR: DRIVER_PASSWORD environment variable is required for the simulator.", file=sys.stderr)
    sys.exit(1)

class FleetSimulator:
    def __init__(self, base_url: str, username: str, driver_id: str, interval: int = 5):
        self.base_url = base_url
        self.username = username
        self.driver_id = driver_id
        self.interval = interval
        self.token = None

    async def authenticate(self):
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            try:
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
            except httpx.RequestError as e:
                print(f"Connection error during authentication: {e}", file=sys.stderr)
                sys.exit(1)

    async def simulate(self):
        await self.authenticate()
        print(f"Simulator started for {self.username} (ID: {self.driver_id}) - Sending updates every {self.interval}s")
        
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            while True:
                lat = 41.8781 + random.uniform(-0.02, 0.02)
                lng = -87.6298 + random.uniform(-0.02, 0.02)
                headers = {
                    "Authorization": f"Bearer {self.token}", 
                    "X-DIAD-Token": DEVICE_API_KEY
                }
                
                try:
                    endpoint = f"/tracking/{self.driver_id}/location"
                    response = await client.post(endpoint, json={
                        "lat": lat,
                        "lon": lng,
                        "speed": random.uniform(0, 45),
                        "heading": random.uniform(0, 360),
                        "battery_level": random.randint(50, 100)
                    }, headers=headers)
                    
                    if response.status_code == 401:
                        print(f"Token expired for {self.username}. Re-authenticating...", file=sys.stderr)
                        await self.authenticate()
                    elif response.status_code == 200:
                        print(f"[{self.username}] Location updated: lat={lat:.4f}, lon={lng:.4f}")
                    else:
                        print(f"[{self.username}] Location update failed: {response.status_code} - {response.text}", file=sys.stderr)
                        
                except httpx.RequestError as e:
                    print(f"Network error during simulation loop: {e}", file=sys.stderr)
                
                await asyncio.sleep(self.interval)