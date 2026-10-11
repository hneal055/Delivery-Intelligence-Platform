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

    # No city/ZIP given: the service area is tried first
    assert calls == ["111 west wacker, Chicago, IL"]
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


@pytest.mark.asyncio
async def test_bare_street_prefers_service_area_over_other_towns(monkeypatch):
    """"1 S State St" also exists in Atkinson, IL; without a city it must
    resolve in the service area, not wherever the geocoder finds it first."""
    async def fake(address):
        if address.endswith("Chicago, IL"):
            return geocoding.GeocodeResult(lat=41.88, lon=-87.63, matched_address="1 S STATE ST, CHICAGO, IL, 60603")
        return geocoding.GeocodeResult(lat=41.42, lon=-90.01, matched_address="1 S STATE STREET PLZ, ATKINSON, IL, 61235")

    monkeypatch.setattr(geocoding, "geocode_address", fake)
    monkeypatch.setattr(geocoding.settings, "SERVICE_AREA_DEFAULT", "Chicago, IL")

    result = await geocoding.geocode_in_service_area("1 S State St")
    assert "CHICAGO" in result.matched_address
    assert result.used_default_area is True


@pytest.mark.asyncio
async def test_falls_back_to_as_typed_when_not_in_service_area(monkeypatch):
    calls = []

    async def fake(address):
        calls.append(address)
        if address.endswith("Chicago, IL"):
            return None
        return geocoding.GeocodeResult(lat=1.0, lon=2.0, matched_address="SOMEWHERE ELSE")

    monkeypatch.setattr(geocoding, "geocode_address", fake)
    monkeypatch.setattr(geocoding.settings, "SERVICE_AREA_DEFAULT", "Chicago, IL")

    result = await geocoding.geocode_in_service_area("1 Unique Rd")
    assert calls == ["1 Unique Rd, Chicago, IL", "1 Unique Rd"]
    assert result.used_default_area is False


def test_names_a_place():
    assert geocoding.names_a_place("100 Main St, Naperville")
    assert geocoding.names_a_place("111 W Wacker Dr 60601")
    assert not geocoding.names_a_place("1 S State St")
    assert not geocoding.names_a_place("111 west wacker dr")
