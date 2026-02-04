from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from src.backend.models.domain import Location
from src.backend.services.routing import routing_service
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

@router.post("/optimize", response_model=RouteOptimizationResponse)
async def optimize_route(
    request: RouteOptimizationRequest,
    authorized: bool = Depends(get_current_device)
):
    """
    Accepts a list of unsorted stops and returns them in the optimal delivery order.
    """
    if not request.stops:
         raise HTTPException(status_code=400, detail="No stops provided")

    sorted_stops = routing_service.optimize_route(
        start_location=request.current_location,
        stops=request.stops
    )
    
    return {
        "optimized_stops": sorted_stops,
        "total_stops": len(sorted_stops),
        "message": "Route optimized successfully using Nearest Neighbor logic."
    }
