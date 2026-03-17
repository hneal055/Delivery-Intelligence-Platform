"""
Unit tests for RedisPubSubManager.
All Redis connections and WebSocket calls are mocked — no live services required.
Covers: connect, disconnect, _run_listener, _connect_redis, _listen_to_redis,
        connect_dispatcher, connect_driver, disconnect_client,
        broadcast_to_dispatchers, send_to_driver, _send_to_local_dispatchers,
        _send_to_local_driver.
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.backend.services.redis_manager import RedisPubSubManager


# ─── helpers ────────────────────────────────────────────────────────────────

def _ws():
    """Return a mock WebSocket with accept/send_json as AsyncMocks."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


# ─── connect() ──────────────────────────────────────────────────────────────

class TestConnect:
    async def test_no_redis_url_returns_early(self):
        mgr = RedisPubSubManager()
        with patch("src.backend.services.redis_manager.settings") as s:
            s.REDIS_URL = None
            await mgr.connect()
        assert mgr._running is False
        assert mgr._listener_task is None

    async def test_with_redis_url_starts_task(self):
        mgr = RedisPubSubManager()

        async def _noop():
            pass

        with patch("src.backend.services.redis_manager.settings") as s:
            s.REDIS_URL = "redis://localhost:6379"
            with patch.object(mgr, "_run_listener", _noop):
                await mgr.connect()
                await asyncio.sleep(0)

        assert mgr._running is True
        assert mgr._listener_task is not None
        if not mgr._listener_task.done():
            mgr._listener_task.cancel()
            try:
                await mgr._listener_task
            except asyncio.CancelledError:
                pass


# ─── disconnect() ───────────────────────────────────────────────────────────

class TestDisconnect:
    async def test_cancels_running_listener_task(self):
        mgr = RedisPubSubManager()

        async def _forever():
            while True:
                await asyncio.sleep(1)

        mgr._running = True
        mgr._listener_task = asyncio.create_task(_forever())

        await mgr.disconnect()

        assert mgr._running is False
        assert mgr._listener_task.cancelled()

    async def test_closes_pubsub_and_redis(self):
        mgr = RedisPubSubManager()
        mock_pubsub = MagicMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()

        mgr._running = True
        mgr.pubsub = mock_pubsub
        mgr.redis = mock_redis

        await mgr.disconnect()

        mock_pubsub.unsubscribe.assert_called_once()
        mock_pubsub.close.assert_called_once()
        mock_redis.aclose.assert_called_once()
        assert mgr.redis is None
        assert mgr.pubsub is None

    async def test_swallows_pubsub_exception(self):
        mgr = RedisPubSubManager()
        mock_pubsub = MagicMock()
        mock_pubsub.unsubscribe = AsyncMock(side_effect=RuntimeError("boom"))
        mock_pubsub.close = AsyncMock()
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock()
        mgr.pubsub = mock_pubsub
        mgr.redis = mock_redis

        await mgr.disconnect()  # must not raise

        assert mgr.redis is None

    async def test_swallows_redis_aclose_exception(self):
        mgr = RedisPubSubManager()
        mock_redis = MagicMock()
        mock_redis.aclose = AsyncMock(side_effect=ConnectionError("closed"))
        mgr.redis = mock_redis

        await mgr.disconnect()  # must not raise

        assert mgr.redis is None

    async def test_already_done_task_not_cancelled_again(self):
        mgr = RedisPubSubManager()

        async def _done():
            pass

        task = asyncio.create_task(_done())
        await asyncio.sleep(0)
        mgr._listener_task = task
        mgr._running = True

        await mgr.disconnect()

        assert mgr._running is False


# ─── _connect_redis() ───────────────────────────────────────────────────────

class TestConnectRedis:
    async def test_creates_client_and_subscribes(self):
        mgr = RedisPubSubManager()
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_redis = MagicMock()
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        with patch("src.backend.services.redis_manager.aioredis") as mock_aioredis:
            with patch("src.backend.services.redis_manager.settings") as s:
                s.REDIS_URL = "redis://localhost:6379"
                mock_aioredis.from_url = MagicMock(return_value=mock_redis)
                await mgr._connect_redis()

        assert mgr.redis is mock_redis
        assert mgr.pubsub is mock_pubsub
        mock_pubsub.subscribe.assert_called_once_with(mgr.channel_name)


# ─── _listen_to_redis() ─────────────────────────────────────────────────────

class TestListenToRedis:
    async def test_skips_non_message_type(self):
        mgr = RedisPubSubManager()
        mgr._running = True

        async def _fake_listen():
            yield {"type": "subscribe", "data": 1}
            yield {
                "type": "message",
                "data": json.dumps({"_target_type": "broadcast", "payload": {"x": 1}}),
            }

        mgr.pubsub = MagicMock()
        mgr.pubsub.listen = _fake_listen
        mgr._send_to_local_dispatchers = AsyncMock()

        await mgr._listen_to_redis()

        # subscribe event skipped; only the broadcast message delivered
        mgr._send_to_local_dispatchers.assert_called_once_with({"x": 1})

    async def test_routes_driver_message(self):
        mgr = RedisPubSubManager()
        mgr._running = True
        payload = {"status": "arrived"}

        async def _fake_listen():
            yield {
                "type": "message",
                "data": json.dumps({
                    "_target_type": "driver",
                    "_target_id": "drv-1",
                    "payload": payload,
                }),
            }

        mgr.pubsub = MagicMock()
        mgr.pubsub.listen = _fake_listen
        mgr._send_to_local_driver = AsyncMock()

        await mgr._listen_to_redis()

        mgr._send_to_local_driver.assert_called_once_with("drv-1", payload)

    async def test_stops_when_not_running(self):
        mgr = RedisPubSubManager()
        mgr._running = False

        async def _fake_listen():
            yield {"type": "message", "data": "{}"}

        mgr.pubsub = MagicMock()
        mgr.pubsub.listen = _fake_listen
        mgr._send_to_local_dispatchers = AsyncMock()

        await mgr._listen_to_redis()

        mgr._send_to_local_dispatchers.assert_not_called()

    async def test_bad_json_does_not_raise(self):
        mgr = RedisPubSubManager()
        mgr._running = True

        async def _fake_listen():
            yield {"type": "message", "data": "NOT_VALID_JSON"}

        mgr.pubsub = MagicMock()
        mgr.pubsub.listen = _fake_listen

        await mgr._listen_to_redis()  # must not propagate the JSON error


# ─── _run_listener() ────────────────────────────────────────────────────────

class TestRunListener:
    async def test_cancelled_error_breaks_loop(self):
        mgr = RedisPubSubManager()
        mgr._running = True

        async def _raise_cancelled():
            raise asyncio.CancelledError()

        with patch.object(mgr, "_connect_redis", _raise_cancelled):
            await mgr._run_listener()
        # exited without re-raising

    async def test_generic_exception_logs_and_exits_when_stopped(self):
        mgr = RedisPubSubManager()
        call_count = 0

        async def _failing_connect():
            nonlocal call_count
            call_count += 1
            mgr._running = False  # stop before sleep
            raise ConnectionError("refused")

        with patch.object(mgr, "_connect_redis", _failing_connect):
            with patch(
                "src.backend.services.redis_manager.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep:
                mgr._running = True
                await mgr._run_listener()

        assert call_count == 1
        mock_sleep.assert_not_called()

    async def test_successful_flow_calls_listen(self):
        mgr = RedisPubSubManager()
        mgr._running = True
        listen_called = False

        async def _good_connect():
            pass

        async def _listen_and_stop():
            nonlocal listen_called
            listen_called = True
            mgr._running = False

        with patch.object(mgr, "_connect_redis", _good_connect):
            with patch.object(mgr, "_listen_to_redis", _listen_and_stop):
                await mgr._run_listener()

        assert listen_called



    async def test_reconnect_sleep_called_between_attempts(self):
        """Cover the asyncio.sleep(reconnect_delay) branch in _run_listener."""
        mgr = RedisPubSubManager()
        call_count = 0

        async def _failing_connect():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                mgr._running = False  # stop loop after 2nd attempt
            raise ConnectionError("refused")

        with patch.object(mgr, "_connect_redis", _failing_connect):
            with patch(
                "src.backend.services.redis_manager.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep:
                mgr._running = True
                await mgr._run_listener()

        mock_sleep.assert_called_once()
        assert call_count == 2
# ─── WebSocket management ───────────────────────────────────────────────────

class TestWebSocketManagement:
    async def test_connect_dispatcher_accepts_and_stores(self):
        mgr = RedisPubSubManager()
        ws = _ws()
        await mgr.connect_dispatcher(ws, "u-1")
        ws.accept.assert_called_once()
        assert mgr.dispatcher_connections["u-1"] is ws

    async def test_connect_driver_accepts_and_stores(self):
        mgr = RedisPubSubManager()
        ws = _ws()
        await mgr.connect_driver(ws, "d-1")
        ws.accept.assert_called_once()
        assert mgr.driver_connections["d-1"] is ws

    def test_disconnect_client_removes_dispatcher(self):
        mgr = RedisPubSubManager()
        ws = _ws()
        mgr.dispatcher_connections["u-1"] = ws
        mgr.disconnect_client("u-1")
        assert "u-1" not in mgr.dispatcher_connections

    def test_disconnect_client_removes_driver(self):
        mgr = RedisPubSubManager()
        ws = _ws()
        mgr.driver_connections["d-1"] = ws
        mgr.disconnect_client("d-1")
        assert "d-1" not in mgr.driver_connections

    def test_disconnect_client_matching_ws_removes(self):
        mgr = RedisPubSubManager()
        ws = _ws()
        mgr.dispatcher_connections["u-1"] = ws
        mgr.disconnect_client("u-1", ws)
        assert "u-1" not in mgr.dispatcher_connections

    def test_disconnect_client_non_matching_ws_keeps_entry(self):
        mgr = RedisPubSubManager()
        ws1 = _ws()
        ws2 = _ws()
        mgr.dispatcher_connections["u-1"] = ws1
        mgr.disconnect_client("u-1", ws2)  # different ws → no removal
        assert "u-1" in mgr.dispatcher_connections

    def test_disconnect_unknown_client_no_error(self):
        mgr = RedisPubSubManager()
        mgr.disconnect_client("nobody")  # no KeyError


# ─── broadcast_to_dispatchers() ─────────────────────────────────────────────

class TestBroadcastToDispatchers:
    async def test_publishes_via_redis_when_available(self):
        mgr = RedisPubSubManager()
        mgr.redis = MagicMock()
        mgr.redis.publish = AsyncMock()

        await mgr.broadcast_to_dispatchers({"event": "update"})

        mgr.redis.publish.assert_called_once()
        channel, raw = mgr.redis.publish.call_args[0]
        assert channel == mgr.channel_name
        data = json.loads(raw)
        assert data["_target_type"] == "broadcast"
        assert data["payload"] == {"event": "update"}

    async def test_local_fallback_when_no_redis(self):
        mgr = RedisPubSubManager()
        mgr.redis = None
        ws = _ws()
        mgr.dispatcher_connections["u-1"] = ws

        await mgr.broadcast_to_dispatchers({"event": "update"})

        ws.send_json.assert_called_once_with({"event": "update"})

    async def test_local_fallback_on_publish_error(self):
        mgr = RedisPubSubManager()
        mgr.redis = MagicMock()
        mgr.redis.publish = AsyncMock(side_effect=ConnectionError("down"))
        ws = _ws()
        mgr.dispatcher_connections["u-1"] = ws

        await mgr.broadcast_to_dispatchers({"event": "retry"})

        ws.send_json.assert_called_once_with({"event": "retry"})


# ─── send_to_driver() ───────────────────────────────────────────────────────

class TestSendToDriver:
    async def test_publishes_via_redis_when_available(self):
        mgr = RedisPubSubManager()
        mgr.redis = MagicMock()
        mgr.redis.publish = AsyncMock()

        await mgr.send_to_driver("d-1", {"status": "assigned"})

        mgr.redis.publish.assert_called_once()
        _, raw = mgr.redis.publish.call_args[0]
        data = json.loads(raw)
        assert data["_target_type"] == "driver"
        assert data["_target_id"] == "d-1"
        assert data["payload"] == {"status": "assigned"}

    async def test_local_fallback_when_no_redis(self):
        mgr = RedisPubSubManager()
        mgr.redis = None
        ws = _ws()
        mgr.driver_connections["d-1"] = ws

        await mgr.send_to_driver("d-1", {"status": "arrived"})

        ws.send_json.assert_called_once_with({"status": "arrived"})

    async def test_local_fallback_on_publish_error(self):
        mgr = RedisPubSubManager()
        mgr.redis = MagicMock()
        mgr.redis.publish = AsyncMock(side_effect=ConnectionError("timeout"))
        ws = _ws()
        mgr.driver_connections["d-1"] = ws

        await mgr.send_to_driver("d-1", {"status": "done"})

        ws.send_json.assert_called_once_with({"status": "done"})


# ─── _send_to_local_dispatchers() ───────────────────────────────────────────

class TestSendToLocalDispatchers:
    async def test_sends_to_all_connected(self):
        mgr = RedisPubSubManager()
        ws1, ws2 = _ws(), _ws()
        mgr.dispatcher_connections = {"a": ws1, "b": ws2}

        await mgr._send_to_local_dispatchers({"msg": "hello"})

        ws1.send_json.assert_called_once_with({"msg": "hello"})
        ws2.send_json.assert_called_once_with({"msg": "hello"})

    async def test_removes_dead_connection(self):
        mgr = RedisPubSubManager()
        dead = MagicMock()
        dead.send_json = AsyncMock(side_effect=RuntimeError("closed"))
        mgr.dispatcher_connections = {"dead": dead}

        await mgr._send_to_local_dispatchers({"msg": "x"})

        assert "dead" not in mgr.dispatcher_connections


# ─── _send_to_local_driver() ────────────────────────────────────────────────

class TestSendToLocalDriver:
    async def test_sends_to_connected_driver(self):
        mgr = RedisPubSubManager()
        ws = _ws()
        mgr.driver_connections = {"d-1": ws}

        await mgr._send_to_local_driver("d-1", {"ping": True})

        ws.send_json.assert_called_once_with({"ping": True})

    async def test_ignores_unconnected_driver(self):
        mgr = RedisPubSubManager()
        await mgr._send_to_local_driver("ghost", {"ping": True})  # no error

    async def test_removes_dead_driver_connection(self):
        mgr = RedisPubSubManager()
        dead = MagicMock()
        dead.send_json = AsyncMock(side_effect=RuntimeError("lost"))
        mgr.driver_connections = {"d-1": dead}

        await mgr._send_to_local_driver("d-1", {"ping": True})

        assert "d-1" not in mgr.driver_connections

