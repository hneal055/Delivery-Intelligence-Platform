"""
Mapbox integration for directions, distance matrix, and geocoding.
Disabled when MAPBOX_ACCESS_TOKEN is empty (all methods return None).
"""

import logging
from typing import Optional, List, Tuple

import httpx

from src.backend.core.config import settings

logger = logging.getLogger(__name__)

MAPBOX_BASE = "https://api.mapbox.com"


class MapboxService:
    def __init__(self):
        self.token = settings.MAPBOX_ACCESS_TOKEN
        self.enabled = bool(self.token)
        if self.enabled:
            logger.info("Mapbox service enabled")
        else:
            logger.info("Mapbox service disabled (no access token)")

    async def get_directions(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        profile: str = "driving",
    ) -> Optional[dict]:
        """
        Get driving directions between two points.
        Returns dict with: distance_km, duration_minutes, geometry (GeoJSON LineString).
        """
        if not self.enabled:
            return None

        coords = f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
        url = f"{MAPBOX_BASE}/directions/v5/mapbox/{profile}/{coords}"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params={
                    "access_token": self.token,
                    "geometries": "geojson",
                    "overview": "full",
                })
                resp.raise_for_status()
                data = resp.json()

            routes = data.get("routes", [])
            if not routes:
                return None

            route = routes[0]
            return {
                "distance_km": route["distance"] / 1000,
                "duration_minutes": route["duration"] / 60,
                "geometry": route["geometry"],
            }
        except Exception as e:
            logger.error(f"Mapbox directions error: {e}")
            return None

    async def get_distance_matrix(
        self,
        coordinates: List[Tuple[float, float]],
        profile: str = "driving",
    ) -> Optional[dict]:
        """
        Get travel time matrix for multiple points.
        Returns dict with: durations (2D list in seconds), distances (2D list in meters).
        """
        if not self.enabled:
            return None

        if len(coordinates) > 25:
            logger.warning("Mapbox matrix limited to 25 coordinates, truncating")
            coordinates = coordinates[:25]

        coords_str = ";".join(f"{lon},{lat}" for lat, lon in coordinates)
        url = f"{MAPBOX_BASE}/directions-matrix/v1/mapbox/{profile}/{coords_str}"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params={
                    "access_token": self.token,
                    "annotations": "duration,distance",
                })
                resp.raise_for_status()
                data = resp.json()

            return {
                "durations": data.get("durations"),
                "distances": data.get("distances"),
            }
        except Exception as e:
            logger.error(f"Mapbox matrix error: {e}")
            return None

    async def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Forward geocode: address string -> (lat, lon).
        Returns None if not found or Mapbox disabled.
        """
        if not self.enabled:
            return None

        url = f"{MAPBOX_BASE}/geocoding/v5/mapbox.places/{address}.json"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params={
                    "access_token": self.token,
                    "limit": 1,
                })
                resp.raise_for_status()
                data = resp.json()

            features = data.get("features", [])
            if not features:
                return None

            lon, lat = features[0]["center"]
            return (lat, lon)
        except Exception as e:
            logger.error(f"Mapbox geocode error: {e}")
            return None

    async def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """
        Reverse geocode: (lat, lon) -> address string.
        Returns None if not found or Mapbox disabled.
        """
        if not self.enabled:
            return None

        url = f"{MAPBOX_BASE}/geocoding/v5/mapbox.places/{lon},{lat}.json"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params={
                    "access_token": self.token,
                    "limit": 1,
                })
                resp.raise_for_status()
                data = resp.json()

            features = data.get("features", [])
            if not features:
                return None

            return features[0].get("place_name")
        except Exception as e:
            logger.error(f"Mapbox reverse geocode error: {e}")
            return None


mapbox_service = MapboxService()
