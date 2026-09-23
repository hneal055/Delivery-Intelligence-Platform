import logging
from typing import Dict, List, Tuple

logger = logging.getLogger("delivery_platform.geofence")

class GeofenceService:
    def __init__(self):
        # Example zones: { zone_id: [(lat, lng), ...] polygon or bounding box }
        self.zones: Dict[str, Dict[str, float]] = {
            "downtown_hub": {"min_lat": 41.8700, "max_lat": 41.8950, "min_lng": -87.6500, "max_lng": -87.6200}
        }

    def check_geofence(self, driver_id: str, lat: float, lng: float) -> List[str]:
        triggered_alerts = []
        for zone_id, box in self.zones.items():
            if box["min_lat"] <= lat <= box["max_lat"] and box["min_lng"] <= lng <= box["max_lng"]:
                triggered_alerts.append(f"Driver {driver_id} entered restricted/monitored zone: {zone_id}")
        return triggered_alerts

geofence_service = GeofenceService()
