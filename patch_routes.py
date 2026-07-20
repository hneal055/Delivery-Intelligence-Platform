import pathlib

ROOT = pathlib.Path(r"C:\Projects\DELIVERYINTELLIGENCEPLATFORM\src\backend\api\routes")

# ── routing.py ───────────────────────────────────────────────────────────────
p = ROOT / "routing.py"
src = p.read_text("utf-8")

# Add Request to fastapi imports
src = src.replace(
    "from fastapi import APIRouter, Depends, HTTPException",
    "from fastapi import APIRouter, Depends, HTTPException, Request",
)
# Add limiter import
src = src.replace(
    "from src.backend.services.auth import get_current_device",
    "from src.backend.services.auth import get_current_device\nfrom src.backend.api.limiter import limiter",
)
# /optimize: rename body param + add decorator + Request
src = src.replace(
    '@router.post("/optimize", response_model=RouteOptimizationResponse)\nasync def optimize_route(\n    request: RouteOptimizationRequest,\n    authorized: bool = Depends(get_current_device)\n):',
    '@router.post("/optimize", response_model=RouteOptimizationResponse)\n@limiter.limit("60/minute")\nasync def optimize_route(\n    request: Request,\n    payload: RouteOptimizationRequest,\n    authorized: bool = Depends(get_current_device)\n):',
)
src = src.replace("    if not request.stops:", "    if not payload.stops:")
src = src.replace(
    "        start_location=request.current_location,\n        stops=request.stops,",
    "        start_location=payload.current_location,\n        stops=payload.stops,",
)
src = src.replace(
    "        start_location=request.current_location,\n        stops=request.stops\n    )",
    "        start_location=payload.current_location,\n        stops=payload.stops\n    )",
)
# /geocode
src = src.replace(
    '@router.post("/geocode", response_model=GeocodeResponse)\nasync def geocode_address(\n    request: GeocodeRequest,\n    authorized: bool = Depends(get_current_device),\n):',
    '@router.post("/geocode", response_model=GeocodeResponse)\n@limiter.limit("30/minute")\nasync def geocode_address(\n    request: Request,\n    payload: GeocodeRequest,\n    authorized: bool = Depends(get_current_device),\n):',
)
src = src.replace("    result = await mapbox_service.geocode(request.address)", "    result = await mapbox_service.geocode(payload.address)")
src = src.replace("    return GeocodeResponse(lat=lat, lon=lon, address=request.address)", "    return GeocodeResponse(lat=lat, lon=lon, address=payload.address)")
# /reverse-geocode
src = src.replace(
    '@router.post("/reverse-geocode", response_model=GeocodeResponse)\nasync def reverse_geocode(\n    request: ReverseGeocodeRequest,\n    authorized: bool = Depends(get_current_device),\n):',
    '@router.post("/reverse-geocode", response_model=GeocodeResponse)\n@limiter.limit("30/minute")\nasync def reverse_geocode(\n    request: Request,\n    payload: ReverseGeocodeRequest,\n    authorized: bool = Depends(get_current_device),\n):',
)
src = src.replace(
    "    address = await mapbox_service.reverse_geocode(request.lat, request.lon)",
    "    address = await mapbox_service.reverse_geocode(payload.lat, payload.lon)",
)
src = src.replace(
    "    return GeocodeResponse(lat=request.lat, lon=request.lon, address=address)",
    "    return GeocodeResponse(lat=payload.lat, lon=payload.lon, address=address)",
)

p.write_text(src, "utf-8")
print("routing.py - @limiter.limit count:", src.count("@limiter.limit"))

# ── advanced_routing.py ──────────────────────────────────────────────────────
p = ROOT / "advanced_routing.py"
src = p.read_text("utf-8")

# Add Request import
src = src.replace(
    "from fastapi import APIRouter, Depends, HTTPException, status",
    "from fastapi import APIRouter, Depends, HTTPException, Request, status",
)
# Add limiter import after db import
src = src.replace(
    "from src.backend.api.deps import get_current_active_user",
    "from src.backend.api.deps import get_current_active_user\nfrom src.backend.api.limiter import limiter",
)
# /time-windows
src = src.replace(
    '@router.post("/time-windows", response_model=TimeWindowResponse, status_code=status.HTTP_200_OK)\nasync def create_time_window(\n    payload: TimeWindowRequest,',
    '@router.post("/time-windows", response_model=TimeWindowResponse, status_code=status.HTTP_200_OK)\n@limiter.limit("60/minute")\nasync def create_time_window(\n    request: Request,\n    payload: TimeWindowRequest,',
)
# /vehicles/profile
src = src.replace(
    '@router.post("/vehicles/profile")\nasync def create_vehicle_profile(\n    payload: VehicleProfileRequest,',
    '@router.post("/vehicles/profile")\n@limiter.limit("60/minute")\nasync def create_vehicle_profile(\n    request: Request,\n    payload: VehicleProfileRequest,',
)
# /optimize-single
src = src.replace(
    '@router.post("/optimize-single")\nasync def optimize_single_route(payload: OptimizeSingleRequest):',
    '@router.post("/optimize-single")\n@limiter.limit("30/minute")\nasync def optimize_single_route(request: Request, payload: OptimizeSingleRequest):',
)
# /optimize-multi-depot
src = src.replace(
    '@router.post("/optimize-multi-depot")\nasync def optimize_multi_depot_route(payload: OptimizeMultiDepotRequest):',
    '@router.post("/optimize-multi-depot")\n@limiter.limit("10/minute")\nasync def optimize_multi_depot_route(request: Request, payload: OptimizeMultiDepotRequest):',
)

p.write_text(src, "utf-8")
print("advanced_routing.py - @limiter.limit count:", src.count("@limiter.limit"))
