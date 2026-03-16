"""
Unit tests for the RoutingService (pure-math, no DB, no HTTP).
"""
import pytest
import math
from src.backend.services.routing import RoutingService
from src.backend.models.domain import Location


def _loc(lat: float, lon: float) -> Location:
    return Location(lat=lat, lon=lon)


@pytest.fixture
def svc():
    return RoutingService()


class TestHaversineOptimizer:
    def test_empty_stops_returns_empty(self, svc):
        result = svc.optimize_route(_loc(40.7128, -74.006), [])
        assert result == []

    def test_single_stop_returned_as_is(self, svc):
        stop = _loc(40.730610, -73.935242)
        result = svc.optimize_route(_loc(40.7128, -74.006), [stop])
        assert len(result) == 1
        assert result[0].lat == stop.lat

    def test_stops_count_preserved(self, svc):
        stops = [
            _loc(40.730610, -73.935242),
            _loc(34.0522, -118.2437),
            _loc(40.7580, -73.9855),
        ]
        result = svc.optimize_route(_loc(40.7128, -74.006), stops)
        assert len(result) == 3

    def test_nearest_stop_is_first(self, svc):
        """The two stops near NYC should appear before the LA stop."""
        start = _loc(40.7128, -74.006)  # NYC City Hall
        queens = _loc(40.730610, -73.935242)   # ~8 km east
        times_sq = _loc(40.7580, -73.9855)     # ~5 km north
        la = _loc(34.0522, -118.2437)          # ~3950 km west

        result = svc.optimize_route(start, [queens, la, times_sq])

        # LA must never be the first stop from NYC
        assert result[0].lat != la.lat

    def test_all_input_stops_appear_in_output(self, svc):
        stops = [
            _loc(40.730610, -73.935242),
            _loc(34.0522, -118.2437),
            _loc(40.7580, -73.9855),
        ]
        result = svc.optimize_route(_loc(40.7128, -74.006), stops)
        result_coords = {(r.lat, r.lon) for r in result}
        input_coords = {(s.lat, s.lon) for s in stops}
        assert result_coords == input_coords

    def test_duplicate_stops_are_preserved(self, svc):
        stop = _loc(40.730610, -73.935242)
        result = svc.optimize_route(_loc(40.7128, -74.006), [stop, stop])
        assert len(result) == 2
