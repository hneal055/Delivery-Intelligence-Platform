"""Final coverage boost: advanced_routing stubs, eta_predictor load, auth gaps."""
import os
import pytest
import joblib
from datetime import datetime, timezone
from unittest.mock import patch
from starlette.requests import Request as StarletteRequest
from sklearn.ensemble import RandomForestRegressor

# ── shared request scope ──────────────────────────────────────────────────────
def _make_req(path: str) -> StarletteRequest:
    return StarletteRequest(scope={
        "type": "http", "method": "POST", "path": path,
        "query_string": b"", "headers": [], "client": ("127.0.0.1", 9000),
    })


# ─── advanced_routing: optimize-single stub ──────────────────────────────────
from src.backend.api.routes.advanced_routing import (
    optimize_single_route, optimize_multi_depot_route,
    OptimizeSingleRequest, OptimizeMultiDepotRequest,
)


@pytest.mark.asyncio
async def test_optimize_single_basic():
    req = _make_req("/advanced-route/optimize-single")
    payload = OptimizeSingleRequest(
        driver_id="D001",
        depot_id="depot-1",
        package_ids=["P1", "P2", "P3"],
        constraints={},
        start_time=datetime.now(timezone.utc),
    )
    result = await optimize_single_route(request=req, payload=payload)
    assert result["driver_id"] == "D001"
    assert result["depot_id"] == "depot-1"
    assert result["stops_count"] == 3
    assert "route_id" in result
    assert result["route_id"].startswith("route-D001-")


@pytest.mark.asyncio
async def test_optimize_single_empty_packages():
    req = _make_req("/advanced-route/optimize-single")
    payload = OptimizeSingleRequest(
        driver_id="DRIVER-X",
        depot_id="depot-main",
        package_ids=[],
        constraints={"max_weight_kg": 500},
        start_time=datetime.now(timezone.utc),
    )
    result = await optimize_single_route(request=req, payload=payload)
    assert result["stops_count"] == 0
    assert "message" in result


@pytest.mark.asyncio
async def test_optimize_multi_depot_basic():
    req = _make_req("/advanced-route/optimize-multi-depot")
    payload = OptimizeMultiDepotRequest(
        depots=[{"id": "D1", "lat": 40.0, "lon": -74.0}, {"id": "D2", "lat": 41.0, "lon": -73.0}],
        stops=[{"id": "S1"}, {"id": "S2"}, {"id": "S3"}],
        available_drivers=["DRV-001", "DRV-002"],
        constraints={},
        optimization_start_time=datetime.now(timezone.utc),
    )
    result = await optimize_multi_depot_route(request=req, payload=payload)
    assert result["depots_count"] == 2
    assert result["stops_count"] == 3
    assert result["drivers_count"] == 2
    assert "route_id" in result
    assert result["route_id"].startswith("multi-")


@pytest.mark.asyncio
async def test_optimize_multi_depot_single():
    req = _make_req("/advanced-route/optimize-multi-depot")
    payload = OptimizeMultiDepotRequest(
        depots=[{"id": "MAIN"}],
        stops=[{"id": "A"}, {"id": "B"}],
        available_drivers=["DRV-1"],
        constraints={"time_limit_minutes": 480},
        optimization_start_time=datetime.now(timezone.utc),
    )
    result = await optimize_multi_depot_route(request=req, payload=payload)
    assert result["depots_count"] == 1
    assert result["stops_count"] == 2
    assert "message" in result


# ─── eta_predictor: _load_model when file exists ─────────────────────────────
from src.analytics.ml_models.eta_predictor import ETAPredictor


def test_load_model_from_existing_file(tmp_path):
    """Covers lines 35-38: _load_model branch when the model file exists."""
    # Train a fresh model and save it to a temp file
    p = ETAPredictor()
    p.train()
    model_path = str(tmp_path / "eta_model.joblib")
    joblib.dump(p.model, model_path)

    # Create a new predictor pointing at that saved file
    p2 = ETAPredictor()
    p2.is_trained = False
    p2.model = None
    p2.model_path = model_path
    p2._load_model()

    assert p2.is_trained is True
    assert p2.model is not None


def test_load_model_corrupt_file(tmp_path):
    """Covers the except branch when a corrupt model file exists."""
    bad_path = str(tmp_path / "corrupt.joblib")
    with open(bad_path, "wb") as f:
        f.write(b"this is not a valid joblib file")

    p = ETAPredictor()
    p.is_trained = False
    p.model = None
    p.model_path = bad_path
    p._load_model()

    # Should not raise; is_trained stays False because load failed
    assert p.is_trained is False


# ─── auth route: OIDC config when enabled ────────────────────────────────────
from src.backend.api.routes.auth import get_oidc_config
from src.backend.core.config import settings


@pytest.mark.asyncio
async def test_oidc_config_enabled():
    """Covers lines 97-99: the enabled=True branch in get_oidc_config."""
    with patch.object(settings, "OIDC_ENABLED", True), \
         patch.object(settings, "OIDC_ISSUER_URL", "https://idp.example.com"), \
         patch.object(settings, "OIDC_CLIENT_ID", "my-client-id"):
        result = await get_oidc_config()
    assert result["enabled"] is True
    assert result["issuer_url"] == "https://idp.example.com"
    assert result["client_id"] == "my-client-id"


# ─── services/auth.py: validate_device_token failure + generate_temp_token ───
from src.backend.services.auth import AuthService
from fastapi import HTTPException
import pytest


def test_generate_temp_token():
    """Covers line 38: generate_temp_token returns expected string."""
    svc = AuthService()
    token = svc.generate_temp_token("driver-99")
    assert token == "session-driver-99-xyz"


@pytest.mark.asyncio
async def test_validate_device_token_invalid_key():
    """Covers line 29: HTTPException raised on wrong key."""
    svc = AuthService()
    with pytest.raises(HTTPException) as exc_info:
        await svc.validate_device_token(api_key_header="wrong-key")
    assert exc_info.value.status_code == 403
