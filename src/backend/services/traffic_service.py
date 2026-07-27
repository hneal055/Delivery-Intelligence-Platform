"""
Traffic and routing service using the TomTom Routing API.

Provides real traffic-adjusted travel time estimates. Falls back to `None`
(never raises) if TOMTOM_API_KEY is not configured or the API call fails for
any reason -- callers are expected to fall back to synthetic estimation in
that case. This service is intentionally never a hard dependency: a TomTom
outage or missing key must not prevent package creation or delivery
confirmation.
"""
import time
import logging
from typing import Optional, TypedDict

import httpx

from src.backend.core.config import settings

logger = logging.getLogger(__name__)

TOMTOM_BASE_URL = "https://api.tomtom.com/routing/1/calculateRoute"
REQUEST_TIMEOUT_SECONDS = 5.0
CACHE_TTL_SECONDS = 300  # 5 minutes
COORD_ROUNDING = 4  # ~11m precision -- coarse enough to get useful cache hits


class TrafficResult(TypedDict):
    traffic_condition: float       # normalized 0.0 (no delay) - 1.0 (heavy delay)
    predicted_eta_seconds: float   # real, traffic-adjusted travel time
    distance_km: float


class TrafficService:
    def __init__(self):
        # cache: {(o_lat, o_lon, d_lat, d_lon): (expires_at, TrafficResult)}
        self._cache: dict[tuple[float, float, float, float], tuple[float, TrafficResult]] = {}

    def _cache_key(
        self, origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float
    ) -> tuple[float, float, float, float]:
        return (
            round(origin_lat, COORD_ROUNDING),
            round(origin_lon, COORD_ROUNDING),
            round(dest_lat, COORD_ROUNDING),
            round(dest_lon, COORD_ROUNDING),
        )

    def _get_cached(self, key) -> Optional[TrafficResult]:
        entry = self._cache.get(key)
        if entry is None:
            return None
        expires_at, result = entry
        if time.time() > expires_at:
            del self._cache[key]
            return None
        return result

    def _set_cached(self, key, result: TrafficResult):
        self._cache[key] = (time.time() + CACHE_TTL_SECONDS, result)

    async def _call_tomtom(
        self, origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float
    ) -> Optional[dict]:
        url = (
            f"{TOMTOM_BASE_URL}/{origin_lat},{origin_lon}:{dest_lat},{dest_lon}/json"
        )
        params = {
            "key": settings.TOMTOM_API_KEY,
            "traffic": "true",
            "travelMode": "car",
        }
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_traffic_data(
        self, origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float
    ) -> Optional[TrafficResult]:
        """
        Return real traffic-adjusted travel data, or None if unavailable.
        Never raises -- all failure modes are caught and logged.
        """
        if not settings.tomtom_configured:
            return None

        key = self._cache_key(origin_lat, origin_lon, dest_lat, dest_lon)
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        last_error: Optional[Exception] = None
        for attempt in range(2):  # one retry on transient failure
            try:
                data = await self._call_tomtom(origin_lat, origin_lon, dest_lat, dest_lon)
                routes = data.get("routes") if data else None
                if not routes:
                    logger.warning("TomTom returned no routes for %s,%s -> %s,%s",
                                    origin_lat, origin_lon, dest_lat, dest_lon)
                    return None

                summary = routes[0]["summary"]
                travel_time = float(summary["travelTimeInSeconds"])
                baseline_time = float(
                    summary.get("noTrafficTravelTimeInSeconds", travel_time)
                )
                length_m = float(summary.get("lengthInMeters", 0.0))

                delay_ratio = 0.0
                if baseline_time > 0:
                    delay_ratio = max(0.0, (travel_time - baseline_time) / baseline_time)
                traffic_condition = min(1.0, delay_ratio)

                result: TrafficResult = {
                    "traffic_condition": traffic_condition,
                    "predicted_eta_seconds": travel_time,
                    "distance_km": length_m / 1000.0,
                }
                self._set_cached(key, result)
                return result

            except (httpx.TimeoutException, httpx.TransportError) as e:
                last_error = e
                logger.warning("TomTom request attempt %d failed (transient): %s", attempt + 1, e)
                continue  # retry once
            except httpx.HTTPStatusError as e:
                logger.warning("TomTom returned HTTP error %s: %s", e.response.status_code, e)
                return None
            except Exception as e:
                logger.warning("Unexpected error calling TomTom: %s", e)
                return None

        logger.warning("TomTom request failed after retry: %s", last_error)
        return None


traffic_service = TrafficService()
