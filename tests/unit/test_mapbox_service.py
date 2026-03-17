"""
Unit tests for MapboxService.
All HTTP calls are mocked via httpx — no network access required.
Covers: get_directions, get_distance_matrix, geocode, reverse_geocode
        (both enabled/disabled paths and error handling).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.backend.services.mapbox import MapboxService


def _make_service(token="fake-token"):
    with patch("src.backend.services.mapbox.settings") as s:
        s.MAPBOX_ACCESS_TOKEN = token
        svc = MapboxService()
    svc.token = token
    svc.enabled = bool(token)
    return svc


def _mock_response(json_data, status=200):
    resp = MagicMock()
    resp.json = MagicMock(return_value=json_data)
    resp.raise_for_status = MagicMock()
    resp.status_code = status
    return resp


# ─── disabled service ───────────────────────────────────────────────────────

class TestMapboxDisabled:
    async def test_get_directions_returns_none(self):
        svc = _make_service(token="")
        result = await svc.get_directions((40.7, -74.0), (40.8, -74.1))
        assert result is None

    async def test_get_distance_matrix_returns_none(self):
        svc = _make_service(token="")
        result = await svc.get_distance_matrix([(40.7, -74.0), (40.8, -74.1)])
        assert result is None

    async def test_geocode_returns_none(self):
        svc = _make_service(token="")
        result = await svc.geocode("123 Main St")
        assert result is None

    async def test_reverse_geocode_returns_none(self):
        svc = _make_service(token="")
        result = await svc.reverse_geocode(40.7, -74.0)
        assert result is None


# ─── get_directions ─────────────────────────────────────────────────────────

class TestGetDirections:
    async def test_success_returns_route_info(self):
        svc = _make_service()
        mock_resp = _mock_response({
            "routes": [{
                "distance": 5000.0,
                "duration": 600.0,
                "geometry": {"type": "LineString", "coordinates": []},
            }]
        })
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("src.backend.services.mapbox.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.get_directions((40.7, -74.0), (40.8, -74.1))

        assert result is not None
        assert result["distance_km"] == 5.0
        assert result["duration_minutes"] == 10.0

    async def test_empty_routes_returns_none(self):
        svc = _make_service()
        mock_resp = _mock_response({"routes": []})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("src.backend.services.mapbox.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.get_directions((40.7, -74.0), (40.8, -74.1))

        assert result is None

    async def test_http_exception_returns_none(self):
        svc = _make_service()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("network error"))

        with patch("src.backend.services.mapbox.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.get_directions((40.7, -74.0), (40.8, -74.1))

        assert result is None


# ─── get_distance_matrix ────────────────────────────────────────────────────

class TestGetDistanceMatrix:
    async def test_success_returns_durations_and_distances(self):
        svc = _make_service()
        mock_resp = _mock_response({
            "durations": [[0, 100], [100, 0]],
            "distances": [[0, 500], [500, 0]],
        })
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("src.backend.services.mapbox.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.get_distance_matrix([(40.7, -74.0), (40.8, -74.1)])

        assert result["durations"] == [[0, 100], [100, 0]]
        assert result["distances"] == [[0, 500], [500, 0]]

    async def test_truncates_over_25_coordinates(self):
        svc = _make_service()
        coords = [(float(i), float(i)) for i in range(30)]
        mock_resp = _mock_response({"durations": [], "distances": []})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("src.backend.services.mapbox.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.get_distance_matrix(coords)

        # Verify the URL only included 25 coords (check call was made)
        call_url = mock_client.get.call_args[0][0]
        assert call_url.count(";") == 24  # 25 coords → 24 separators

    async def test_exception_returns_none(self):
        svc = _make_service()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("timeout"))

        with patch("src.backend.services.mapbox.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.get_distance_matrix([(40.7, -74.0)])

        assert result is None


# ─── geocode ────────────────────────────────────────────────────────────────

class TestGeocode:
    async def test_success_returns_lat_lon(self):
        svc = _make_service()
        mock_resp = _mock_response({
            "features": [{"center": [-74.006, 40.7128]}]
        })
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("src.backend.services.mapbox.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.geocode("New York City")

        assert result == (40.7128, -74.006)

    async def test_empty_features_returns_none(self):
        svc = _make_service()
        mock_resp = _mock_response({"features": []})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("src.backend.services.mapbox.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.geocode("nowhere")

        assert result is None

    async def test_exception_returns_none(self):
        svc = _make_service()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("DNS failure"))

        with patch("src.backend.services.mapbox.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.geocode("broken")

        assert result is None


# ─── reverse_geocode ────────────────────────────────────────────────────────

class TestReverseGeocode:
    async def test_success_returns_place_name(self):
        svc = _make_service()
        mock_resp = _mock_response({
            "features": [{"place_name": "40 Wall St, New York"}]
        })
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("src.backend.services.mapbox.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.reverse_geocode(40.7128, -74.006)

        assert result == "40 Wall St, New York"

    async def test_empty_features_returns_none(self):
        svc = _make_service()
        mock_resp = _mock_response({"features": []})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("src.backend.services.mapbox.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.reverse_geocode(0.0, 0.0)

        assert result is None

    async def test_exception_returns_none(self):
        svc = _make_service()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("rate limited"))

        with patch("src.backend.services.mapbox.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.reverse_geocode(40.7, -74.0)

        assert result is None
