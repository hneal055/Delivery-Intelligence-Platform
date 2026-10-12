"""POST /tracking/{driver_id}/location: drivers move only their own dot.

The drivers table has a PostGIS column the SQLite test DB cannot create, so
the DB session and the location service are stand-ins here.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.backend.api.deps import get_current_active_user, get_db
from src.backend.api.main import app
from src.backend.api.routes import tracking

POINT = {"lat": 41.7428, "lon": -87.5545, "speed": 8.0, "heading": 90.0}


@pytest_asyncio.fixture
async def make_client(monkeypatch):
    update = AsyncMock()
    broadcast = AsyncMock()
    monkeypatch.setattr(tracking, "update_driver_location", update)
    monkeypatch.setattr(tracking.manager, "broadcast_to_dispatchers", broadcast)
    db = MagicMock()
    db.commit = AsyncMock()
    clients = []

    async def _make(user):
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_active_user] = lambda: user
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        clients.append(client)
        return client, update, broadcast

    yield _make
    for client in clients:
        await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_driver_updates_own_location(make_client, driver_user):
    client, update, broadcast = await make_client(driver_user)
    resp = await client.post("/tracking/driver_test/location", json=POINT)
    assert resp.status_code == 200
    assert update.await_args.kwargs["driver_id"] == "driver_test"
    sent = broadcast.await_args.args[0]
    assert sent["type"] == "driver_location"
    assert sent["driver_id"] == "driver_test"
    assert sent["lat"] == pytest.approx(41.7428)


@pytest.mark.asyncio
async def test_driver_cannot_move_another_driver(make_client, driver_user):
    client, update, broadcast = await make_client(driver_user)
    resp = await client.post("/tracking/driver2/location", json=POINT)
    assert resp.status_code == 403
    update.assert_not_awaited()
    broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_manager_may_update_any_driver(make_client, manager_user):
    client, update, _ = await make_client(manager_user)
    resp = await client.post("/tracking/driver2/location", json=POINT)
    assert resp.status_code == 200
    assert update.await_args.kwargs["driver_id"] == "driver2"
    assert update.await_args.kwargs["name"] == "driver2"


@pytest.mark.asyncio
async def test_broadcast_failure_does_not_fail_update(make_client, driver_user):
    client, _, broadcast = await make_client(driver_user)
    broadcast.side_effect = RuntimeError("redis down")
    resp = await client.post("/tracking/driver_test/location", json=POINT)
    assert resp.status_code == 200
