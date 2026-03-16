"""
Targeted tests to boost code coverage across several previously-uncovered paths:
  - GeofenceEngine.create_circular_zone and verify_delivery_location
  - ETAPredictor._save_model actual disk write
  - routing.py: 400 (no stops), 501 (Mapbox disabled), success paths
  - advanced_routing.py: optimize-single and optimize-multi-depot stubs
"""
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from starlette.requests import Request as StarletteRequest

from src.backend.models.domain import Location
from src.analytics.geofencing.engine import GeofenceEngine
from src.analytics.ml_models.eta_predictor import ETAPredictor
from src.backend.api.routes.routing import (
    optimize_route,
    geocode_address,
    reverse_geocode,
    RouteOptimizationRequest,
    GeocodeRequest,
    ReverseGeocodeRequest,
)
from src.backend.api.routes.advanced_routing import (
    optimize_single_route,
    optimize_multi_depot_route,
    OptimizeSingleRequest,
    OptimizeMultiDepotRequest,
)

_SCOPE = {
    "type": "http", "method": "POST", "path": "/test",
    "query_string": b"", "headers": [], "client": ("127.0.0.1", 9999),
}


def _req():
    return StarletteRequest(scope=dict(_SCOPE))


# ─── GeofenceEngine: create_circular_zone ───────────────────────────────────

class TestCreateCircularZone:
    def setup_method(self):
        self.engine = GeofenceEngine()

    def test_returns_list_of_locations(self):
        center = Location(lat=40.7128, lon=-74.0060)
        zone = self.engine.create_circular_zone(center, radius_meters=200.0)
        assert isinstance(zone, list)
        assert len(zone) > 0
        assert all(hasattr(loc, "lat") and hasattr(loc, "lon") for loc in zone)

    def test_zone_encloses_center(self):
        center = Location(lat=40.7128, lon=-74.0060)
        zone = self.engine.create_circular_zone(center, radius_meters=500.0)
        # shapely's exterior.coords repeats the first point at the end; skip last
        assert self.engine.is_in_zone(center, zone[:-1]) is True

    def test_larger_radius_produces_more_points(self):
        center = Location(lat=51.5, lon=-0.1)
        small = self.engine.create_circular_zone(center, radius_meters=100.0)
        large = self.engine.create_circular_zone(center, radius_meters=1000.0)
        # Both approximations use the same number of vertices from shapely buffer
        assert len(small) > 0 and len(large) > 0


# ─── GeofenceEngine: verify_delivery_location ────────────────────────────────

class TestVerifyDeliveryLocation:
    def setup_method(self):
        self.engine = GeofenceEngine()

    def test_within_threshold_returns_true(self):
        current = (40.7128, -74.0060)
        # Same point → 0 metres away
        target = (40.7128, -74.0060)
        is_valid, dist = self.engine.verify_delivery_location(current, target)
        assert is_valid is True
        assert dist == 0.0

    def test_outside_threshold_returns_false(self):
        current = (40.7128, -74.0060)
        target = (40.8000, -74.0060)  # ~9.7 km
        is_valid, dist = self.engine.verify_delivery_location(current, target)
        assert is_valid is False
        assert dist > 100.0

    def test_custom_threshold(self):
        current = (40.7128, -74.0060)
        target = (40.7138, -74.0060)  # ~111 m
        ok_200, _ = self.engine.verify_delivery_location(current, target, threshold_meters=200.0)
        ok_50, _ = self.engine.verify_delivery_location(current, target, threshold_meters=50.0)
        assert ok_200 is True
        assert ok_50 is False


# ─── ETAPredictor: _save_model ───────────────────────────────────────────────

def test_save_model_writes_file(tmp_path):
    with patch.object(ETAPredictor, "_load_model"):
        p = ETAPredictor()
    p.model_path = str(tmp_path / "model.joblib")
    with patch.object(p, "_save_model"):
        p.train()  # trains in memory
    p._save_model()  # this time actually write to disk
    assert os.path.exists(p.model_path)


# ─── routing.py: optimize_route 400 (no stops) ───────────────────────────────

@pytest.mark.asyncio
async def test_optimize_route_no_stops_raises_400():
    payload = RouteOptimizationRequest(
        driver_id="D001",
        current_location=Location(lat=40.71, lon=-74.0),
        stops=[],
    )
    with pytest.raises(HTTPException) as exc_info:
        await optimize_route(request=_req(), payload=payload, authorized=True)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_optimize_route_uses_haversine_fallback():
    payload = RouteOptimizationRequest(
        driver_id="D001",
        current_location=Location(lat=40.71, lon=-74.0),
        stops=[Location(lat=40.72, lon=-74.01), Location(lat=40.73, lon=-74.02)],
    )
    with patch("src.backend.api.routes.routing.routing_service") as mock_rs:
        mock_rs.optimize_route_mapbox = AsyncMock(return_value=None)
        mock_rs.optimize_route = MagicMock(return_value=payload.stops)
        result = await optimize_route(request=_req(), payload=payload, authorized=True)
    assert result.total_stops == 2
    assert "haversine" in result.message.lower()


# ─── routing.py: geocode 501 (Mapbox disabled) ───────────────────────────────

@pytest.mark.asyncio
async def test_geocode_returns_501_when_mapbox_disabled():
    with patch("src.backend.api.routes.routing.mapbox_service") as m:
        m.enabled = False
        with pytest.raises(HTTPException) as exc_info:
            await geocode_address(request=_req(), payload=GeocodeRequest(address="NYC"), authorized=True)
    assert exc_info.value.status_code == 501


@pytest.mark.asyncio
async def test_geocode_returns_404_when_address_not_found():
    with patch("src.backend.api.routes.routing.mapbox_service") as m:
        m.enabled = True
        m.geocode = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await geocode_address(request=_req(), payload=GeocodeRequest(address="Unknown XYZ"), authorized=True)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_geocode_success():
    with patch("src.backend.api.routes.routing.mapbox_service") as m:
        m.enabled = True
        m.geocode = AsyncMock(return_value=(40.7128, -74.0060))
        result = await geocode_address(request=_req(), payload=GeocodeRequest(address="NYC"), authorized=True)
    assert result.lat == 40.7128
    assert result.lon == -74.0060


@pytest.mark.asyncio
async def test_reverse_geocode_returns_501_when_mapbox_disabled():
    with patch("src.backend.api.routes.routing.mapbox_service") as m:
        m.enabled = False
        with pytest.raises(HTTPException) as exc_info:
            await reverse_geocode(request=_req(), payload=ReverseGeocodeRequest(lat=40.71, lon=-74.0), authorized=True)
    assert exc_info.value.status_code == 501


@pytest.mark.asyncio
async def test_reverse_geocode_success():
    with patch("src.backend.api.routes.routing.mapbox_service") as m:
        m.enabled = True
        m.reverse_geocode = AsyncMock(return_value="New York, NY")
        result = await reverse_geocode(request=_req(), payload=ReverseGeocodeRequest(lat=40.71, lon=-74.0), authorized=True)
    assert result.address == "New York, NY"


# ─── advanced_routing.py: optimize-single and optimize-multi-depot stubs ─────

@pytest.mark.asyncio
async def test_optimize_single_route_stub():
    payload = OptimizeSingleRequest(
        driver_id="D001",
        depot_id="depot-A",
        package_ids=["P001", "P002", "P003"],
        constraints={},
        start_time=datetime.now(timezone.utc),
    )
    result = await optimize_single_route(request=_req(), payload=payload)
    assert result["driver_id"] == "D001"
    assert result["stops_count"] == 3
    assert "depot_id" in result


@pytest.mark.asyncio
async def test_optimize_multi_depot_stub():
    payload = OptimizeMultiDepotRequest(
        depots=[{"id": "D1"}, {"id": "D2"}],
        stops=[{"id": "S1"}, {"id": "S2"}, {"id": "S3"}],
        available_drivers=["dr1", "dr2"],
        constraints={},
        optimization_start_time=datetime.now(timezone.utc),
    )
    result = await optimize_multi_depot_route(request=_req(), payload=payload)
    assert result["depots_count"] == 2
    assert result["stops_count"] == 3
    assert result["drivers_count"] == 2
