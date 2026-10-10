"""
Address -> coordinates using the US Census Bureau geocoder.

Free, no API key, covers US street addresses (all of Chicagoland). Returns
None when the address cannot be matched or the service is unreachable, so
callers can ask the dispatcher to correct the address.
https://geocoding.geo.census.gov/geocoder/
"""
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
TIMEOUT_SECONDS = 10.0


@dataclass
class GeocodeResult:
    lat: float
    lon: float
    matched_address: str


async def geocode_address(address: str) -> Optional[GeocodeResult]:
    params = {"address": address, "benchmark": "Public_AR_Current", "format": "json"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.get(CENSUS_URL, params=params)
            response.raise_for_status()
            matches = response.json()["result"]["addressMatches"]
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        logger.warning("Census geocoder failed for %r: %s", address, exc)
        return None

    if not matches:
        return None
    best = matches[0]
    return GeocodeResult(
        lat=best["coordinates"]["y"],
        lon=best["coordinates"]["x"],
        matched_address=best["matchedAddress"],
    )
