import json
import logging
import asyncio
from typing import Dict, Optional
from fastapi import WebSocket
from redis import asyncio as aioredis
from src.backend.core.config import settings

logger = logging.getLogger(__name__)

class RedisPubSubManager:
    """
    Manages WebSocket connections and syncs messages across backend instances using Redis Pub/Sub.
    """
    def __init__(self):
        self.dispatcher_connections: Dict[str, WebSocket] = {}
        self.driver_connections: Dict[str, WebSocket] = {}
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self.channel_name = "delivery_platform_broadcast"

    async def connect(self):
        """Initialize Redis connection and start listener task."""
        if not settings.REDIS_URL:
            logger.warning("REDIS_URL not set. Falling back to in-memory mode (no multi-node sync).")
            return

        try:
            self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe(self.channel_name)
            logger.info(f"Connected to Redis Pub/Sub channel: {self.channel_name}")
            
            # Start background listener
            asyncio.create_task(self._listen_to_redis())
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None

    async def _listen_to_redis(self):
        """Background task to listen for Redis messages and forward to local WebSockets."""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    target_type = data.get("_target_type")
                    target_id = data.get("_target_id")
                    payload = data.get("payload")

                    if target_type == "broadcast":
                        await self._send_to_local_dispatchers(payload)
                    elif target_type == "driver":
                        await self._send_to_local_driver(target_id, payload)
        except Exception as e:
            logger.error(f"Error in Redis listener: {e}")

    async def connect_dispatcher(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.dispatcher_connections[user_id] = websocket
        logger.info(f"Dispatcher {user_id} connected (Local). Total: {len(self.dispatcher_connections)}")

    async def connect_driver(self, websocket: WebSocket, driver_id: str):
        await websocket.accept()
        self.driver_connections[driver_id] = websocket
        logger.info(f"Driver {driver_id} connected (Local). Total: {len(self.driver_connections)}")

    def disconnect(self, user_id: str, websocket: WebSocket = None):
        if user_id in self.dispatcher_connections:
            if websocket is None or self.dispatcher_connections[user_id] is websocket:
                del self.dispatcher_connections[user_id]
        if user_id in self.driver_connections:
            if websocket is None or self.driver_connections[user_id] is websocket:
                del self.driver_connections[user_id]

    async def broadcast_to_dispatchers(self, message: dict):
        """
        Publish message to Redis for all instances to receive.
        If Redis is down/disabled, send locally and log warning.
        """
        if self.redis:
            wrapper = {
                "_target_type": "broadcast",
                "payload": message
            }
            await self.redis.publish(self.channel_name, json.dumps(wrapper))
        else:
            await self._send_to_local_dispatchers(message)

    async def send_to_driver(self, driver_id: str, message: dict):
        """
        Publish message to Redis. Only the instance holding the driver connection will deliver it.
        """
        if self.redis:
            wrapper = {
                "_target_type": "driver",
                "_target_id": driver_id,
                "payload": message
            }
            await self.redis.publish(self.channel_name, json.dumps(wrapper))
        else:
            await self._send_to_local_driver(driver_id, message)

    async def _send_to_local_dispatchers(self, message: dict):
        """Internal: Deliver message to locally connected dispatchers."""
        to_remove = []
        for uid, ws in self.dispatcher_connections.items():
            try:
                await ws.send_json(message)
            except Exception:
                to_remove.append(uid)
        for uid in to_remove:
            self.dispatcher_connections.pop(uid, None)

    async def _send_to_local_driver(self, driver_id: str, message: dict):
        """Internal: Deliver message to locally connected driver if present."""
        ws = self.driver_connections.get(driver_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.driver_connections.pop(driver_id, None)

manager = RedisPubSubManager()

