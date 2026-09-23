import asyncio
import json
import logging
from typing import List
from fastapi import WebSocket
from src.backend.services.geofence import geofence_service
from src.backend.services.sla_monitor import sla_monitor
import redis.asyncio as aioredis

logger = logging.getLogger("delivery_platform.websockets")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.redis_client = None
        self.pubsub_task = None

    async def initialize_redis(self, redis_url: str = "redis://localhost:6379"):
        try:
            self.redis_client = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
            self.pubsub_task = asyncio.create_task(self._redis_listener())
            logger.info("Redis Pub/Sub listener initialized for WebSockets.")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis Pub/Sub: {e}")

    async def _redis_listener(self):
        if not self.redis_client:
            return
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("fleet_telemetry_channel")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    event_type = data.get("event", "update")
                    event_data = data.get("data", {})
                    
                    await self._local_broadcast(event_type, event_data)

                    # Check geofences on location updates
                    if event_type == "location_update" and "driver_id" in event_data:
                        alerts = geofence_service.check_geofence(
                            event_data["driver_id"],
                            event_data.get("lat", 0.0),
                            event_data.get("lng", 0.0)
                        )
                        for alert in alerts:
                            alert_payload = {"driver_id": event_data["driver_id"], "message": alert}
                            await self._local_broadcast("geofence_alert", alert_payload)

                        # Check SLA & stationarity incidents
                        sla_alerts = sla_monitor.evaluate_telemetry(
                            event_data["driver_id"],
                            event_data.get("lat", 0.0),
                            event_data.get("lng", 0.0),
                            event_data.get("speed", 0.0)
                        )
                        for sla_alert in sla_alerts:
                            sla_payload = {"driver_id": event_data["driver_id"], "message": sla_alert}
                            await self._local_broadcast("sla_alert", sla_payload)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis listener error: {e}")

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Dispatcher connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Dispatcher disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, event: str, data: dict):
        """Publishes to Redis so all backend instances broadcast to their clients."""
        payload = json.dumps({"event": event, "data": data})
        if self.redis_client:
            await self.redis_client.publish("fleet_telemetry_channel", payload)
        else:
            await self._local_broadcast(event, data)

    async def _local_broadcast(self, event: str, data: dict):
        payload = json.dumps({"event": event, "data": data})
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        for dead in disconnected:
            self.disconnect(dead)

    async def shutdown(self):
        if self.pubsub_task:
            self.pubsub_task.cancel()
        if self.redis_client:
            await self.redis_client.close()

manager = ConnectionManager()
