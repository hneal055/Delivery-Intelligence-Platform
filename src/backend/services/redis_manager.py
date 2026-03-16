import json
import logging
import asyncio
from typing import Dict, Optional
from fastapi import WebSocket
from redis import asyncio as aioredis
from src.backend.core.config import settings

logger = logging.getLogger(__name__)

_RECONNECT_DELAY_SECONDS = 5


class RedisPubSubManager:
    """
    Manages WebSocket connections and syncs messages across backend instances using Redis Pub/Sub.
    Includes automatic reconnection on Redis failure and graceful shutdown.
    """

    def __init__(self):
        self.dispatcher_connections: Dict[str, WebSocket] = {}
        self.driver_connections: Dict[str, WebSocket] = {}
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self.channel_name = "delivery_platform_broadcast"
        self._listener_task: Optional[asyncio.Task] = None
        self._running: bool = False

    async def connect(self):
        """Initialize Redis connection and start background listener task."""
        if not settings.REDIS_URL:
            logger.warning("REDIS_URL not set. Falling back to in-memory mode (no multi-node sync).")
            return

        self._running = True
        self._listener_task = asyncio.create_task(self._run_listener())
        logger.info("Redis Pub/Sub listener task started.")

    async def disconnect(self):
        """Graceful shutdown: cancel listener task and close Redis connections."""
        self._running = False
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self.pubsub:
            try:
                await self.pubsub.unsubscribe(self.channel_name)
                await self.pubsub.close()
            except Exception:
                pass

        if self.redis:
            try:
                await self.redis.aclose()
            except Exception:
                pass

        self.redis = None
        self.pubsub = None
        logger.info("Redis Pub/Sub manager disconnected cleanly.")

    async def _run_listener(self):
        """
        Outer loop: reconnect whenever the Redis connection drops.
        Retries every _RECONNECT_DELAY_SECONDS seconds.
        """
        while self._running:
            try:
                await self._connect_redis()
                logger.info(f"Redis Pub/Sub subscribed to channel: {self.channel_name}")
                await self._listen_to_redis()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Redis Pub/Sub connection error: {e}. Reconnecting in {_RECONNECT_DELAY_SECONDS}s...")
                self.redis = None
                self.pubsub = None

            if self._running:
                await asyncio.sleep(_RECONNECT_DELAY_SECONDS)

    async def _connect_redis(self):
        """Create fresh Redis client and subscribe to broadcast channel."""
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(self.channel_name)

    async def _listen_to_redis(self):
        """Inner loop: read messages from pubsub and fan out to local WebSockets."""
        async for message in self.pubsub.listen():
            if not self._running:
                break
            if message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
                target_type = data.get("_target_type")
                target_id = data.get("_target_id")
                payload = data.get("payload")

                if target_type == "broadcast":
                    await self._send_to_local_dispatchers(payload)
                elif target_type == "driver":
                    await self._send_to_local_driver(target_id, payload)
            except Exception as e:
                logger.error(f"Error processing Redis message: {e}")

    async def connect_dispatcher(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.dispatcher_connections[user_id] = websocket
        logger.info(f"Dispatcher {user_id} connected. Total: {len(self.dispatcher_connections)}")

    async def connect_driver(self, websocket: WebSocket, driver_id: str):
        await websocket.accept()
        self.driver_connections[driver_id] = websocket
        logger.info(f"Driver {driver_id} connected. Total: {len(self.driver_connections)}")

    def disconnect_client(self, user_id: str, websocket: WebSocket = None):
        if user_id in self.dispatcher_connections:
            if websocket is None or self.dispatcher_connections[user_id] is websocket:
                del self.dispatcher_connections[user_id]
        if user_id in self.driver_connections:
            if websocket is None or self.driver_connections[user_id] is websocket:
                del self.driver_connections[user_id]

    async def broadcast_to_dispatchers(self, message: dict):
        """Publish message to Redis for all instances; falls back to local if Redis is down."""
        if self.redis:
            wrapper = {"_target_type": "broadcast", "payload": message}
            try:
                await self.redis.publish(self.channel_name, json.dumps(wrapper))
                return
            except Exception as e:
                logger.warning(f"Redis publish failed, delivering locally: {e}")
        await self._send_to_local_dispatchers(message)

    async def send_to_driver(self, driver_id: str, message: dict):
        """Publish to Redis; only the instance holding this driver's socket delivers it."""
        if self.redis:
            wrapper = {
                "_target_type": "driver",
                "_target_id": driver_id,
                "payload": message,
            }
            try:
                await self.redis.publish(self.channel_name, json.dumps(wrapper))
                return
            except Exception as e:
                logger.warning(f"Redis publish failed, delivering locally: {e}")
        await self._send_to_local_driver(driver_id, message)

    async def _send_to_local_dispatchers(self, message: dict):
        to_remove = []
        for uid, ws in list(self.dispatcher_connections.items()):
            try:
                await ws.send_json(message)
            except Exception:
                to_remove.append(uid)
        for uid in to_remove:
            self.dispatcher_connections.pop(uid, None)

    async def _send_to_local_driver(self, driver_id: str, message: dict):
        ws = self.driver_connections.get(driver_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.driver_connections.pop(driver_id, None)


manager = RedisPubSubManager()
