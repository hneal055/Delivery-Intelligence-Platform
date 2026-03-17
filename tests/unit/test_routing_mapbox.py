"""
Unit tests for RoutingService.optimize_route_mapbox (Mapbox travel-time matrix path).
Complements test_routing_service.py which covers the haversine/2-opt fallback.
"""
import pytest
from unittest.mock import AsyncMock, patch

from src.backend.services.routing import RoutingService
from src.backend.models.domain import Location


def _loc(lat, lon):
    return Location(lat=lat, lon=lon)


START = _loc(40.7128, -74.006)
STOPS = [_loc(40.73, -73.93), _loc(34.05, -118.24), _loc(40.75, -73.98)]


class TestOptimizeRouteMapbox:
    async def test_returns_none_when_mapbox_disabled(self):
        svc = RoutingService()
        with patch("src.backend.services.routing.mapbox_service") as ms:
            ms.enabled = False
            result = await svc.optimize_route_mapbox(START, STOPS)
        assert result is None

    async def test_returns_none_when_stops_empty(self):
        svc = RoutingService()
        with patch("src.backend.services.routing.mapbox_service") as ms:
            ms.enabled = True
            result = await svc.optimize_route_mapbox(START, [])
        assert result is None

    async def test_returns_none_when_matrix_call_returns_none(self):
        svc = RoutingService()
        with patch("src.backend.services.routing.mapbox_service") as ms:
            ms.enabled = True
            ms.get_distance_matrix = AsyncMock(return_value=None)
            result = await svc.optimize_route_mapbox(START, STOPS)
        assert result is None

    async def test_returns_none_when_durations_missing(self):
        svc = RoutingService()
        with patch("src.backend.services.routing.mapbox_service") as ms:
            ms.enabled = True
            ms.get_distance_matrix = AsyncMock(return_value={"durations": None})
            result = await svc.optimize_route_mapbox(START, STOPS)
        assert result is None

    async def test_returns_optimized_stops_only(self):
        """Result must contain every stop (not the start) in some order."""
        svc = RoutingService()
        n = 4
        durations = [[abs(i - j) * 100.0 for j in range(n)] for i in range(n)]

        with patch("src.backend.services.routing.mapbox_service") as ms:
            ms.enabled = True
            ms.get_distance_matrix = AsyncMock(return_value={"durations": durations})
            result = await svc.optimize_route_mapbox(START, STOPS)

        assert result is not None
        assert len(result) == 3
        result_coords = {(r.lat, r.lon) for r in result}
        stop_coords = {(s.lat, s.lon) for s in STOPS}
        assert result_coords == stop_coords

    async def test_skips_none_duration_edges(self):
        """Edges with None duration should be excluded from nearest-neighbour."""
        svc = RoutingService()
        stops_2 = [_loc(40.73, -73.93), _loc(40.75, -73.98)]
        # 3x3 matrix (start + 2 stops); start→stop1 is None (unreachable first hop)
        durations = [
            [0, None, 200],
            [None, 0, 50],
            [200, 50, 0],
        ]

        with patch("src.backend.services.routing.mapbox_service") as ms:
            ms.enabled = True
            ms.get_distance_matrix = AsyncMock(return_value={"durations": durations})
            result = await svc.optimize_route_mapbox(START, stops_2)

        assert result is not None
        assert len(result) == 2


    async def test_breaks_when_no_reachable_next_node(self):
        """Cover the break branch when best_next is None in nearest-neighbour."""
        svc = RoutingService()
        # From start(0): stop1 reachable(100), stop2 unreachable(None)
        # From stop1(1): stop2 unreachable(None) → best_next=None → break
        durations = [
            [0,   100,  None],
            [100,   0,  None],
            [None, None,   0],
        ]
        stops_2 = [_loc(40.73, -73.93), _loc(40.75, -73.98)]

        with patch("src.backend.services.routing.mapbox_service") as ms:
            ms.enabled = True
            ms.get_distance_matrix = AsyncMock(return_value={"durations": durations})
            result = await svc.optimize_route_mapbox(START, stops_2)

        # Only stop1 was reachable before the break; partial route returned
        assert result is not None
        assert len(result) == 1
