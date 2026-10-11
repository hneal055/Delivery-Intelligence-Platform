import asyncio
import json
import os
import random
import redis.asyncio as aioredis

async def simulate_fleet():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        client = await aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        print("Connected to Redis for standalone fleet simulation.")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        return

    drivers = [
        {"driver_id": "driver_01", "lat": 41.8781, "lng": -87.6298},
        {"driver_id": "driver_02", "lat": 41.8900, "lng": -87.6500},
        {"driver_id": "driver_03", "lat": 41.8500, "lng": -87.6000},
    ]

    print("Starting live telemetry broadcast stream... Press Ctrl+C to stop.")
    try:
        while True:
            for driver in drivers:
                # Simulate small movement
                driver["lat"] += random.uniform(-0.001, 0.001)
                driver["lng"] += random.uniform(-0.001, 0.001)
                
                payload = {
                    "event": "location_update",
                    "data": {
                        "driver_id": driver["driver_id"],
                        "lat": driver["lat"],
                        "lng": driver["lng"],
                        "speed": round(random.uniform(15.0, 55.0), 1),
                        "heading": round(random.uniform(0.0, 360.0), 1),
                        "timestamp": asyncio.get_event_loop().time()
                    }
                }
                
                await client.publish("fleet_telemetry_channel", json.dumps(payload))
                print(f"Broadcasted telemetry for {driver["driver_id"]}: lat={driver["lat"]:.4f}, lng={driver["lng"]:.4f}")
            
            await asyncio.sleep(2.0)
    except asyncio.CancelledError:
        pass
    finally:
        await client.close()

if __name__ == "__main__":
    try:
        asyncio.run(simulate_fleet())
    except KeyboardInterrupt:
        print("Simulation stopped by user.")
