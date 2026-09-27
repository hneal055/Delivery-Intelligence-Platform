import asyncio
import json
import logging
import os
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://delivery_redis:6379")
PROXIMITY_THRESHOLD_METERS = 50.0

async def trigger_push_notification(driver_id: str, package_id: str, distance: float):
    """Simulate sending a push notification to the operations center and driver mobile app."""
    logger.warning(
        f"*** PUSH NOTIFICATION DISPATCHED *** Driver {driver_id} is within "
        f"{distance:.2f}m of target for package {package_id} (Threshold: <= {PROXIMITY_THRESHOLD_METERS}m)."
    )

async def alert_worker():
    """Consume Redis Pub/Sub fleet events and evaluate geofence proximity triggers."""
    logger.info("Starting automated geofence alert worker service...")
    client = aioredis.from_url(REDIS_URL, decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe("fleet_events", "telemetry_updates")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                channel = message["channel"]
                raw_data = message["data"]
                
                try:
                    # Attempt JSON parsing if event payloads are structured
                    event = json.loads(raw_data) if raw_data.startswith("{") else {"raw": raw_data}
                    driver_id = event.get("driver_id", "D-UNKNOWN")
                    package_id = event.get("package_id", "PKG-UNKNOWN")
                    distance = float(event.get("distance_meters", 9999.0))
                    
                    if distance <= PROXIMITY_THRESHOLD_METERS:
                        await trigger_push_notification(driver_id, package_id, distance)
                except json.JSONDecodeError:
                    # Handle raw string announcements from Redis pub/sub
                    if "delivered" in raw_data.lower() or "arrived" in raw_data.lower():
                        logger.info(f"Fleet Event Received [{channel}]: {raw_data}")
        
    except Exception as e:
        logger.error(f"Error in alert worker listener: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(alert_worker())