import math
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DEFAULT_GEOFENCE_RADIUS_METERS = 50.0

# In-memory tracking of active arrivals to prevent duplicate triggers
# Schema: { f"{driver_id}_{package_id}": { "arrived_at": datetime, "notified": bool } }
ACTIVE_ARRIVALS: Dict[str, Dict[str, Any]] = {}

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)

async def check_geofences_for_driver(
    driver_id: str,
    current_lat: float,
    current_lon: float,
    assigned_packages: Optional[List[Dict[str, Any]]] = None,
    radius_meters: float = DEFAULT_GEOFENCE_RADIUS_METERS
) -> List[Dict[str, Any]]:
    """
    Evaluates driver GPS proximity against all open packages.
    Returns list of newly triggered arrival events.
    """
    if assigned_packages is None:
        # Default active packages for simulation
        assigned_packages = [
            {"id": "pkg-001", "address": "100 N State St, Chicago, IL", "lat": 41.8837, "lon": -87.6278, "status": "OUT_FOR_DELIVERY"},
            {"id": "pkg-002", "address": "231 S Michigan Ave, Chicago, IL", "lat": 41.8789, "lon": -87.6247, "status": "OUT_FOR_DELIVERY"},
            {"id": "pkg-003", "address": "500 W Madison St, Chicago, IL", "lat": 41.8819, "lon": -87.6398, "status": "OUT_FOR_DELIVERY"},
            {"id": "pkg-004", "address": "400 N Michigan Ave, Chicago, IL", "lat": 41.8900, "lon": -87.6240, "status": "OUT_FOR_DELIVERY"},
            {"id": "pkg-005", "address": "222 W Merchandise Mart Plaza", "lat": 41.8885, "lon": -87.6354, "status": "OUT_FOR_DELIVERY"},
        ]

    arrival_events = []
    now = datetime.now(timezone.utc)

    for pkg in assigned_packages:
        pkg_id = pkg["id"]
        if pkg.get("status") in ["DELIVERED", "CANCELLED"]:
            continue

        dist = haversine_distance_meters(current_lat, current_lon, pkg["lat"], pkg["lon"])
        arrival_key = f"{driver_id}_{pkg_id}"

        if dist <= radius_meters:
            if arrival_key not in ACTIVE_ARRIVALS:
                ACTIVE_ARRIVALS[arrival_key] = {
                    "arrived_at": now.isoformat(),
                    "distance_meters": dist,
                    "notified": True,
                }
                event = {
                    "event_type": "DRIVER_ARRIVED",
                    "driver_id": driver_id,
                    "package_id": pkg_id,
                    "address": pkg["address"],
                    "distance_meters": dist,
                    "arrived_at": now.isoformat(),
                    "message": f"Driver {driver_id} arrived within {dist}m of {pkg['address']}",
                }
                arrival_events.append(event)
                logger.info(f"[Geofence Trigger] {event['message']}")
        else:
            # Clear geofence entry once driver departs outside 150m buffer
            if arrival_key in ACTIVE_ARRIVALS and dist > (radius_meters * 3):
                ACTIVE_ARRIVALS.pop(arrival_key, None)

    return arrival_events
