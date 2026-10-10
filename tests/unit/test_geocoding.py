import httpx
import pytest

from src.backend.services import geocoding


def _client_returning(handler):
    real = httpx.AsyncClient
    return lambda **kw: real(transport=httpx.MockTransport(handler), **kw)


@pytest.mark.asyncio
async def test_parses_census_match(monkeypatch):
    body = {"result": {"addressMatches": [{
        "matchedAddress": "222 W MERCHANDISE MART PLZ, CHICAGO, IL, 60654",
        "coordinates": {"x": -87.6343, "y": 41.8880},
    }]}}
    monkeypatch.setattr(geocoding.httpx, "AsyncClient",
                        _client_returning(lambda req: httpx.Response(200, json=body)))

    result = await geocoding.geocode_address("222 W Merchandise Mart Plaza, Chicago")

    assert (result.lat, result.lon) == (41.8880, -87.6343)
    assert result.matched_address.startswith("222 W MERCHANDISE")


@pytest.mark.asyncio
async def test_no_match_returns_none(monkeypatch):
    monkeypatch.setattr(geocoding.httpx, "AsyncClient",
                        _client_returning(lambda req: httpx.Response(200, json={"result": {"addressMatches": []}})))
    assert await geocoding.geocode_address("nowhere") is None


@pytest.mark.asyncio
async def test_service_error_returns_none(monkeypatch):
    monkeypatch.setattr(geocoding.httpx, "AsyncClient",
                        _client_returning(lambda req: httpx.Response(503)))
    assert await geocoding.geocode_address("anything") is None
