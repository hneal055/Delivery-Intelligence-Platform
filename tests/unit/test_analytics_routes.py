"""
Unit tests for analytics route functions called directly.
Uses a minimal real Starlette Request so slowapi rate-limit enforcement
proceeds without raising a type validation exception.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from starlette.requests import Request as StarletteRequest

from src.backend.api.routes.analytics import (
    predict_delivery_time,
    ETARequest,
    train_model_synthetic,
)

_HTTP_SCOPE = {
    "type": "http",
    "method": "POST",
    "path": "/analytics/predict-eta",
    "query_string": b"",
    "headers": [],
    "client": ("127.0.0.1", 9999),
}


def _real_request() -> StarletteRequest:
    """Minimal real Starlette Request that satisfies slowapi type check."""
    return StarletteRequest(scope=dict(_HTTP_SCOPE))


def _mock_user(role: str = "admin"):
    user = MagicMock()
    user.role = role
    return user


@pytest.mark.asyncio
async def test_predict_eta_returns_ml_result_without_mapbox():
    payload = ETARequest(distance_km=5.0, traffic_load=0.5, num_packages=2)
    with patch("src.backend.api.routes.analytics.mapbox_service") as mock_mapbox:
        mock_mapbox.get_directions = AsyncMock(return_value=None)
        result = await predict_delivery_time(
            request=_real_request(), payload=payload, current_user=_mock_user()
        )
    assert result.estimated_minutes >= 1.0
    assert result.source == "ml"


@pytest.mark.asyncio
async def test_predict_eta_blends_with_mapbox_directions():
    payload = ETARequest(
        distance_km=5.0, traffic_load=0.4, num_packages=1,
        origin_lat=40.71, origin_lon=-74.0,
        dest_lat=40.75, dest_lon=-73.98,
    )
    with patch("src.backend.api.routes.analytics.mapbox_service") as mock_mapbox:
        mock_mapbox.get_directions = AsyncMock(return_value={"duration_minutes": 18.0})
        result = await predict_delivery_time(
            request=_real_request(), payload=payload, current_user=_mock_user()
        )
    assert result.source == "blended"
    assert result.mapbox_minutes == 18.0


@pytest.mark.asyncio
async def test_predict_eta_negative_distance_raises_400():
    payload = ETARequest(distance_km=-1.0, traffic_load=0.5, num_packages=1)
    with pytest.raises(HTTPException) as exc_info:
        await predict_delivery_time(
            request=_real_request(), payload=payload, current_user=_mock_user()
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_train_model_synthetic_returns_success():
    with patch("src.backend.api.routes.analytics.eta_predictor") as mock_pred:
        mock_pred.train = MagicMock()
        result = await train_model_synthetic(
            request=_real_request(), current_user=_mock_user()
        )
    assert "trained" in result["message"].lower()
    mock_pred.train.assert_called_once()
