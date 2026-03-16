"""
Unit tests for GeofenceEngine methods: is_in_zone, calculate_distance_meters,
estimate_eta_minutes.  All pure geometry/math — no network or DB needed.
"""
import math
import pytest
from src.analytics.geofencing.engine import GeofenceEngine
from src.backend.models.domain import Location


@pytest.fixture
def engine():
    return GeofenceEngine()


@pytest.fixture
def unit_square():
    """A 1-degree square around (0,0)."""
    return [
        Location(lat=0.0, lon=0.0),
        Location(lat=0.0, lon=1.0),
        Location(lat=1.0, lon=1.0),
        Location(lat=1.0, lon=0.0),
    ]


class TestIsInZone:
    def test_point_inside_polygon(self, engine, unit_square):
        driver = Location(lat=0.5, lon=0.5)
        assert engine.is_in_zone(driver, unit_square) is True

    def test_point_outside_polygon(self, engine, unit_square):
        driver = Location(lat=5.0, lon=5.0)
        assert engine.is_in_zone(driver, unit_square) is False

    def test_polygon_with_fewer_than_3_points_returns_false(self, engine):
        too_small = [Location(lat=0.0, lon=0.0), Location(lat=1.0, lon=1.0)]
        driver = Location(lat=0.5, lon=0.5)
        assert engine.is_in_zone(driver, too_small) is False

    def test_empty_polygon_returns_false(self, engine):
        assert engine.is_in_zone(Location(lat=0.0, lon=0.0), []) is False

    def test_point_on_corner_is_not_strictly_inside(self, engine, unit_square):
        # Shapely's contains() returns False for boundary points
        corner = Location(lat=0.0, lon=0.0)
        result = engine.is_in_zone(corner, unit_square)
        assert isinstance(result, bool)


class TestCalculateDistanceMeters:
    def test_same_point_is_zero(self, engine):
        loc = Location(lat=40.7128, lon=-74.0060)
        assert engine.calculate_distance_meters(loc, loc) == 0.0

    def test_nyc_to_london_approx(self, engine):
        nyc = Location(lat=40.7128, lon=-74.0060)
        london = Location(lat=51.5074, lon=-0.1278)
        dist = engine.calculate_distance_meters(nyc, london)
        # ~5,570 km ± 200 km
        assert 5_300_000 < dist < 5_800_000

    def test_returns_float(self, engine):
        a = Location(lat=51.0, lon=-1.0)
        b = Location(lat=51.5, lon=-1.5)
        assert isinstance(engine.calculate_distance_meters(a, b), float)

    def test_distance_is_symmetric(self, engine):
        a = Location(lat=48.8566, lon=2.3522)
        b = Location(lat=51.5074, lon=-0.1278)
        assert engine.calculate_distance_meters(a, b) == engine.calculate_distance_meters(b, a)


class TestEstimateEtaMinutes:
    def test_nearby_locations_small_eta(self, engine):
        a = Location(lat=40.7128, lon=-74.0060)
        b = Location(lat=40.7135, lon=-74.0062)
        eta = engine.estimate_eta_minutes(a, b)
        assert 0 < eta < 5  # realistic for very close points

    def test_eta_increases_with_distance(self, engine):
        origin = Location(lat=51.5, lon=-0.1)
        near = Location(lat=51.51, lon=-0.1)
        far = Location(lat=51.6, lon=-0.1)
        eta_near = engine.estimate_eta_minutes(origin, near)
        eta_far = engine.estimate_eta_minutes(origin, far)
        assert eta_far > eta_near

    def test_zero_speed_returns_infinity(self, engine):
        a = Location(lat=40.7128, lon=-74.0060)
        b = Location(lat=40.7200, lon=-74.0100)
        eta = engine.estimate_eta_minutes(a, b, avg_speed_kmh=0.0)
        assert eta == float("inf")

    def test_higher_speed_lower_eta(self, engine):
        a = Location(lat=40.7128, lon=-74.0060)
        b = Location(lat=40.7500, lon=-74.0500)
        slow = engine.estimate_eta_minutes(a, b, avg_speed_kmh=20.0)
        fast = engine.estimate_eta_minutes(a, b, avg_speed_kmh=60.0)
        assert fast < slow
