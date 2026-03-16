"""
Unit tests for geofencing pure-logic functions.
Uses Shapely directly — no DB, no HTTP, no PostGIS required.
"""
import pytest
from src.backend.models.domain import Location
from src.analytics.geofencing.core import is_in_delivery_zone


def _loc(lat: float, lon: float) -> Location:
    return Location(lat=lat, lon=lon)


# Simple square zone: lat 41-42, lon -88 to -87
SQUARE_ZONE = [
    _loc(41.0, -88.0),
    _loc(42.0, -88.0),
    _loc(42.0, -87.0),
    _loc(41.0, -87.0),
    _loc(41.0, -88.0),  # close the ring
]


class TestIsInDeliveryZone:
    def test_point_inside_zone(self):
        inside = _loc(41.5, -87.5)  # centre of square
        assert is_in_delivery_zone(inside, SQUARE_ZONE) is True

    def test_point_outside_zone(self):
        outside = _loc(43.0, -87.5)  # north of square
        assert is_in_delivery_zone(outside, SQUARE_ZONE) is False

    def test_point_on_boundary_is_not_inside(self):
        # Shapely's .contains() is exclusive of the boundary
        on_edge = _loc(41.0, -87.5)
        assert is_in_delivery_zone(on_edge, SQUARE_ZONE) is False

    def test_far_away_point_is_outside(self):
        far = _loc(34.0522, -118.2437)  # Los Angeles
        assert is_in_delivery_zone(far, SQUARE_ZONE) is False

    def test_different_zone_same_point(self):
        # Build a triangular zone around Chicago downtown
        triangle = [
            _loc(41.85, -87.65),
            _loc(41.90, -87.60),
            _loc(41.85, -87.60),
            _loc(41.85, -87.65),  # close ring
        ]
        inside_tri = _loc(41.87, -87.62)
        outside_tri = _loc(41.80, -87.65)
        assert is_in_delivery_zone(inside_tri, triangle) is True
        assert is_in_delivery_zone(outside_tri, triangle) is False
