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


@pytest.mark.asyncio
async def test_service_area_retry_when_city_missing(monkeypatch):
    calls = []

    async def fake(address):
        calls.append(address)
        if address.endswith("Chicago, IL"):
            return geocoding.GeocodeResult(lat=1.0, lon=2.0, matched_address="111 W WACKER DR, CHICAGO, IL, 60601")
        return None

    monkeypatch.setattr(geocoding, "geocode_address", fake)
    monkeypatch.setattr(geocoding.settings, "SERVICE_AREA_DEFAULT", "Chicago, IL")

    result = await geocoding.geocode_in_service_area("111 west wacker")

    assert calls == ["111 west wacker", "111 west wacker, Chicago, IL"]
    assert result.used_default_area is True


@pytest.mark.asyncio
async def test_no_retry_when_area_already_given(monkeypatch):
    calls = []

    async def fake(address):
        calls.append(address)
        return None

    monkeypatch.setattr(geocoding, "geocode_address", fake)
    monkeypatch.setattr(geocoding.settings, "SERVICE_AREA_DEFAULT", "Chicago, IL")

    assert await geocoding.geocode_in_service_area("1 Nowhere St, Chicago, IL") is None
    assert calls == ["1 Nowhere St, Chicago, IL"]


@pytest.mark.asyncio
async def test_direct_match_is_not_marked_default(monkeypatch):
    async def fake(address):
        return geocoding.GeocodeResult(lat=1.0, lon=2.0, matched_address="X")

    monkeypatch.setattr(geocoding, "geocode_address", fake)
    result = await geocoding.geocode_in_service_area("100 Main St, Naperville, IL")
    assert result.used_default_area is False
