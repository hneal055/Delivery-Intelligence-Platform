import asyncio
import json
import os
import logging
import redis.asyncio as aioredis

logger = logging.getLogger("delivery_platform.telemetry_worker")
logging.basicConfig(level=logging.INFO)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

async def run_telemetry_worker():
    try:
        client = await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe("fleet_telemetry_channel")
        logger.info("Telemetry persistence worker successfully connected to Redis Pub/Sub.")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    raw = json.loads(message["data"])
                    if raw.get("event") == "location_update":
                        data = raw.get("data", {})
                        driver_id = data.get("driver_id")
                        lat = data.get("lat")
                        lng = data.get("lng")
                        logger.info(f"Persisting telemetry audit breadcrumb -> Driver: {driver_id} | Lat: {lat:.4f}, Lng: {lng:.4f}")
                except Exception as ex:
                    logger.error(f"Failed to process telemetry message: {ex}")
    except Exception as e:
        logger.error(f"Worker connection error: {e}")

if __name__ == "__main__":
    asyncio.run(run_telemetry_worker())
