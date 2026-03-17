"""
E2E tests: PostGIS-specific geometry storage and spatial queries.

These tests verify that the application correctly uses PostGIS geometry
columns, GiST indexed spatial queries, and ST_DWithin / ST_Distance operators.
They only run when E2E_DATABASE_URL points to a real PostgreSQL + PostGIS DB.
"""
import uuid
import pytest
from sqlalchemy import text

from src.backend.models.sql_models import Driver, Package, LocationHistory
from src.backend.utils.security import get_password_hash


pytestmark = pytest.mark.e2e


# ── Geometry column storage ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_driver_geometry_stored_and_retrieved(e2e_db):
    """Writing lat/lon + WKT geometry round-trips correctly via PostGIS."""
    driver_id = f"E2E-{uuid.uuid4().hex[:8]}"
    lat, lon = 41.8781, -87.6298  # Willis Tower, Chicago

    driver = Driver(
        id=driver_id,
        name="PostGIS E2E Driver",
        status="active",
        current_lat=lat,
        current_lon=lon,
        location=f"SRID=4326;POINT({lon} {lat})",
    )
    e2e_db.add(driver)
    await e2e_db.flush()

    # Read back via raw ST_AsText to confirm PostGIS parsed the geometry
    row = await e2e_db.execute(
        text("SELECT ST_AsText(location) AS wkt FROM drivers WHERE id = :id"),
        {"id": driver_id},
    )
    wkt = row.scalar_one()
    assert wkt is not None
    assert "POINT" in wkt.upper()
    # PostGIS returns POINT(-87.6298 41.8781) — lon first (x,y)
    assert f"{lon}" in wkt and f"{lat}" in wkt


@pytest.mark.asyncio
async def test_package_geometry_stored(e2e_db):
    """destination_location geometry column stores and compiles correctly."""
    driver = Driver(id=f"E2E-{uuid.uuid4().hex[:8]}", name="Pkg Driver", status="active")
    e2e_db.add(driver)
    await e2e_db.flush()

    lat, lon = 40.7128, -74.0060  # New York
    pkg = Package(
        id=str(uuid.uuid4()),
        driver_id=driver.id,
        dest_lat=lat,
        dest_lon=lon,
        status="pending",
        destination_location=f"SRID=4326;POINT({lon} {lat})",
    )
    e2e_db.add(pkg)
    await e2e_db.flush()

    row = await e2e_db.execute(
        text("SELECT ST_AsText(destination_location) FROM packages WHERE id = :id"),
        {"id": pkg.id},
    )
    wkt = row.scalar_one()
    assert wkt is not None and "POINT" in wkt.upper()


# ── Spatial query operators ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_st_dwithin_nearby_drivers(e2e_db):
    """ST_DWithin correctly identifies drivers within 1 km of a reference point."""
    # Reference: Chicago Loop  42.8781, -87.6298
    ref_lat, ref_lon = 41.8781, -87.6298

    nearby_id = f"E2E-NEAR-{uuid.uuid4().hex[:6]}"
    far_id    = f"E2E-FAR-{uuid.uuid4().hex[:6]}"

    # Nearby driver — same block (~50 m away)
    nearby_lat, nearby_lon = 41.8785, -87.6295
    e2e_db.add(Driver(
        id=nearby_id, name="Nearby Driver", status="active",
        current_lat=nearby_lat, current_lon=nearby_lon,
        location=f"SRID=4326;POINT({nearby_lon} {nearby_lat})",
    ))

    # Far driver — ~15 km north
    far_lat, far_lon = 42.0, -87.6298
    e2e_db.add(Driver(
        id=far_id, name="Far Driver", status="active",
        current_lat=far_lat, current_lon=far_lon,
        location=f"SRID=4326;POINT({far_lon} {far_lat})",
    ))

    await e2e_db.flush()

    # ST_DWithin uses geography type for metre-accurate radius (1 km = 1000 m)
    result = await e2e_db.execute(
        text("""
            SELECT id FROM drivers
            WHERE ST_DWithin(
                location::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                1000
            )
        """),
        {"lat": ref_lat, "lon": ref_lon},
    )
    found_ids = {row.id for row in result}

    assert nearby_id in found_ids, "Nearby driver should be within 1 km"
    assert far_id not in found_ids, "Far driver should be outside 1 km"


@pytest.mark.asyncio
async def test_st_distance_returns_metres(e2e_db):
    """ST_Distance (geography) returns distance in metres between two known points."""
    # Haversine distance from Willis Tower to Navy Pier ≈ 2.7 km
    result = await e2e_db.execute(
        text("""
            SELECT ST_Distance(
                ST_SetSRID(ST_MakePoint(-87.6298, 41.8781), 4326)::geography,
                ST_SetSRID(ST_MakePoint(-87.6011, 41.8917), 4326)::geography
            ) AS dist_m
        """)
    )
    dist_m = result.scalar_one()
    # Should be roughly 2700 m ± 10 %
    assert 2400 < dist_m < 3000, f"Expected ~2700 m, got {dist_m:.0f} m"


@pytest.mark.asyncio
async def test_gist_index_exists_on_drivers(e2e_db):
    """Confirm GiST spatial index exists on drivers.location (from migration)."""
    result = await e2e_db.execute(
        text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'drivers'
              AND indexdef ILIKE '%gist%'
              AND indexdef ILIKE '%location%'
        """)
    )
    rows = result.fetchall()
    assert len(rows) >= 1, "Expected at least one GiST index on drivers.location"


# ── Location history with geometry ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_location_history_geometry_insert(e2e_db):
    """LocationHistory geometry column stores multiple points per driver."""
    driver = Driver(id=f"E2E-{uuid.uuid4().hex[:8]}", name="History Driver", status="active")
    e2e_db.add(driver)
    await e2e_db.flush()

    points = [(41.8781, -87.6298), (41.8790, -87.6310), (41.8800, -87.6325)]
    for lat, lon in points:
        e2e_db.add(LocationHistory(
            id=str(uuid.uuid4()),
            driver_id=driver.id,
            lat=lat,
            lon=lon,
            location=f"SRID=4326;POINT({lon} {lat})",
        ))
    await e2e_db.flush()

    result = await e2e_db.execute(
        text("""
            SELECT COUNT(*) FROM location_history
            WHERE driver_id = :did AND location IS NOT NULL
        """),
        {"did": driver.id},
    )
    count = result.scalar_one()
    assert count == 3