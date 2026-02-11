from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from src.backend.models.domain import Location
from src.backend.services.routing import routing_service
from src.backend.services.mapbox import mapbox_service
from src.backend.services.auth import get_current_device

router = APIRouter(prefix="/route", tags=["routing"])


class RouteOptimizationRequest(BaseModel):
    driver_id: str
    current_location: Location
    stops: List[Location]


class RouteOptimizationResponse(BaseModel):
    optimized_stops: List[Location]
    total_stops: int
    message: str
    route_geometry: Optional[dict] = None


@router.post("/optimize", response_model=RouteOptimizationResponse)
async def optimize_route(
    request: RouteOptimizationRequest,
    authorized: bool = Depends(get_current_device)
):
    """
    Accepts a list of unsorted stops and returns them in the optimal delivery order.
    Uses Mapbox travel-time matrix when available, falls back to haversine.
    """
    if not request.stops:
        raise HTTPException(status_code=400, detail="No stops provided")

    # Try Mapbox-powered optimization first
    mapbox_result = await routing_service.optimize_route_mapbox(
        start_location=request.current_location,
        stops=request.stops,
    )

    if mapbox_result is not None:
        return RouteOptimizationResponse(
            optimized_stops=mapbox_result,
            total_stops=len(mapbox_result),
            message="Route optimized using Mapbox travel-time matrix.",
        )

    # Fallback to haversine
    sorted_stops = routing_service.optimize_route(
        start_location=request.current_location,
        stops=request.stops
    )

    return RouteOptimizationResponse(
        optimized_stops=sorted_stops,
        total_stops=len(sorted_stops),
        message="Route optimized using haversine distance (Mapbox unavailable).",
    )


class GeocodeRequest(BaseModel):
    address: str


class GeocodeResponse(BaseModel):
    lat: float
    lon: float
    address: str


@router.post("/geocode", response_model=GeocodeResponse)
async def geocode_address(
    request: GeocodeRequest,
    authorized: bool = Depends(get_current_device),
):
    """Forward geocode: convert address string to lat/lon coordinates."""
    if not mapbox_service.enabled:
        raise HTTPException(status_code=501, detail="Geocoding requires Mapbox access token")

    result = await mapbox_service.geocode(request.address)
    if result is None:
        raise HTTPException(status_code=404, detail="Address not found")

    lat, lon = result
    return GeocodeResponse(lat=lat, lon=lon, address=request.address)


class ReverseGeocodeRequest(BaseModel):
    lat: float
    lon: float


@router.post("/reverse-geocode", response_model=GeocodeResponse)
async def reverse_geocode(
    request: ReverseGeocodeRequest,
    authorized: bool = Depends(get_current_device),
):
    """Reverse geocode: convert lat/lon coordinates to address string."""
    if not mapbox_service.enabled:
        raise HTTPException(status_code=501, detail="Geocoding requires Mapbox access token")

    address = await mapbox_service.reverse_geocode(request.lat, request.lon)
    if address is None:
        raise HTTPException(status_code=404, detail="Location not found")

    return GeocodeResponse(lat=request.lat, lon=request.lon, address=address)
