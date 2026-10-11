"""
Address -> coordinates using the US Census Bureau geocoder.

Free, no API key, covers US street addresses (all of Chicagoland). Returns
None when the address cannot be matched or the service is unreachable, so
callers can ask the dispatcher to correct the address.
https://geocoding.geo.census.gov/geocoder/
"""
import logging
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from src.backend.core.config import settings

logger = logging.getLogger(__name__)

CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
TIMEOUT_SECONDS = 10.0


@dataclass
class GeocodeResult:
    lat: float
    lon: float
    matched_address: str
    used_default_area: bool = False


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


_ZIP = re.compile(r"\b\d{5}(-\d{4})?\b")


def names_a_place(address: str) -> bool:
    """True if the address already says where it is: a comma (street, city)
    or a ZIP code. (A trailing two-letter word is NOT treated as a state:
    "St", "Dr" and "Av" end most street names.)"""
    text = address.strip()
    return "," in text or bool(_ZIP.search(text))


async def geocode_in_service_area(address: str) -> Optional[GeocodeResult]:
    """Geocode an address the way a local dispatcher types it.

    "1 S State St" alone matches 1 S State St in *Atkinson, IL*, not Chicago,
    so an address that names no city, state or ZIP is tried in the service
    area FIRST ("1 S State St, Chicago, IL"), and only then as typed. An
    address that already names its place is used as typed. The result says
    whether the service area was added, so the dispatcher can confirm it."""
    area = settings.SERVICE_AREA_DEFAULT.strip()
    if area and not names_a_place(address) and area.lower() not in address.lower():
        result = await geocode_address(f"{address}, {area}")
        if result is not None:
            result.used_default_area = True
            return result
        return await geocode_address(address)

    result = await geocode_address(address)
    if result is not None or not area or area.lower() in address.lower():
        return result
    result = await geocode_address(f"{address}, {area}")
    if result is not None:
        result.used_default_area = True
    return result
