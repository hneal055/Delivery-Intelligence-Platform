"""
E2E tests: full-stack API against real PostgreSQL + PostGIS.

Exercises the complete request path — FastAPI → SQLAlchemy → PostGIS — for
the most critical business flows, including geometry-backed location tracking.
"""
import uuid
import pytest

from src.backend.models.sql_models import User as UserSQL, Driver as DriverSQL
from src.backend.models.domain import UserRole
from src.backend.utils.security import get_password_hash


pytestmark = pytest.mark.e2e


# ── Seed helpers ──────────────────────────────────────────────────────────────

async def _create_user(db, role: UserRole = UserRole.MANAGER):
    tag = uuid.uuid4().hex[:6]
    u = UserSQL(
        id=str(uuid.uuid4()),
        username=f"e2e_{role.value}_{tag}",
        email=f"e2e_{tag}@test.invalid",
        hashed_password=get_password_hash("Password1!"),
        role=role.value,
        is_active=True,
    )
    db.add(u)
    await db.flush()
    return u


async def _create_driver(db, name="E2E Driver"):
    d = DriverSQL(id=f"E2E-{uuid.uuid4().hex[:8]}", name=name, status="active")
    db.add(d)
    await db.flush()
    return d


# ── Auth flow ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_real_db_login(e2e_client):
    """Login with a user seeded directly into real PostgreSQL succeeds."""
    client, db = e2e_client
    user = await _create_user(db, UserRole.MANAGER)
    await db.commit()

    resp = await client.post(
        "/auth/token",
        data={"username": user.username, "password": "Password1!", "grant_type": "password"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


# ── Location tracking with real geometry ──────────────────────────────────────

@pytest.mark.asyncio
async def test_update_driver_location_writes_geometry(e2e_client):
    """PUT /tracking/location writes a PostGIS geometry point for the driver."""
    from src.backend.api.deps import get_current_active_user
    from src.backend.api.main import app
    from src.backend.models.domain import User
    from sqlalchemy import text

    client, db = e2e_client
    driver = await _create_driver(db, "Geometry Test Driver")
    user_sql = await _create_user(db, UserRole.DRIVER)
    await db.commit()

    domain_user = User(
        id=user_sql.id,
        username=user_sql.username,
        email=user_sql.email,
        role=UserRole.DRIVER,
        is_active=True,
    )
    app.dependency_overrides[get_current_active_user] = lambda: domain_user

    try:
        resp = await client.put(
            "/tracking/location",
            json={"driver_id": driver.id, "lat": 41.8781, "lon": -87.6298, "speed": 30.0},
        )
        assert resp.status_code == 200

        # Verify geometry was actually written to PostGIS
        row = await db.execute(
            text("SELECT ST_AsText(location) FROM drivers WHERE id = :id"),
            {"id": driver.id},
        )
        wkt = row.scalar_one()
        assert wkt is not None, "PostGIS geometry should have been written"
        assert "POINT" in wkt.upper()
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_location_history_stored_with_geometry(e2e_client):
    """Subsequent location updates accumulate in location_history with geometry."""
    from src.backend.api.deps import get_current_active_user
    from src.backend.api.main import app
    from src.backend.models.domain import User
    from sqlalchemy import text

    client, db = e2e_client
    driver = await _create_driver(db, "History Geometry Driver")
    user_sql = await _create_user(db, UserRole.DRIVER)
    await db.commit()

    domain_user = User(
        id=user_sql.id, username=user_sql.username, email=user_sql.email,
        role=UserRole.DRIVER, is_active=True,
    )
    app.dependency_overrides[get_current_active_user] = lambda: domain_user

    try:
        waypoints = [
            (41.8781, -87.6298),
            (41.8790, -87.6310),
            (41.8800, -87.6325),
        ]
        for lat, lon in waypoints:
            resp = await client.put(
                "/tracking/location",
                json={"driver_id": driver.id, "lat": lat, "lon": lon},
            )
            assert resp.status_code == 200

        result = await db.execute(
            text("""
                SELECT COUNT(*) FROM location_history
                WHERE driver_id = :did AND location IS NOT NULL
            """),
            {"did": driver.id},
        )
        count = result.scalar_one()
        assert count >= 3, f"Expected ≥3 geometry rows in location_history, got {count}"
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


# ── Dispatch with real FK constraints ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_and_assign_job_real_db(e2e_client):
    """Create a dispatch job and assign it to a driver using real PostgreSQL FK checks."""
    from src.backend.api.deps import get_current_active_user
    from src.backend.api.main import app
    from src.backend.models.domain import User

    client, db = e2e_client
    driver = await _create_driver(db, "Dispatch FK Driver")
    mgr_sql = await _create_user(db, UserRole.MANAGER)
    await db.commit()

    domain_mgr = User(
        id=mgr_sql.id, username=mgr_sql.username, email=mgr_sql.email,
        role=UserRole.MANAGER, is_active=True,
    )
    app.dependency_overrides[get_current_active_user] = lambda: domain_mgr

    try:
        # Create job
        resp = await client.post(
            "/dispatch/jobs",
            json={"title": "E2E Real DB Job", "type": "delivery", "priority": "high"},
        )
        assert resp.status_code == 201
        job_id = resp.json()["id"]

        # Assign to real driver (FK constraint enforced by PostgreSQL)
        resp = await client.put(f"/dispatch/jobs/{job_id}/assign/{driver.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "assigned"
        assert resp.json()["driver_id"] == driver.id
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


# ── Health smoke ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint_with_real_db(e2e_client):
    """/health returns 200 when the real DB connection is healthy."""
    client, _ = e2e_client
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "online"