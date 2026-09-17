import math
from typing import Optional, Dict, List
from src.backend.services.heartbeat import heartbeat_service

class DispatchService:
    def __init__(self):
        # Simulated driver coordinates cache for matching (latitude, longitude)
        self.driver_locations: Dict[str, tuple[float, float]] = {
            f"D{i:03d}": (41.8781 + (i * 0.01), -87.6298 - (i * 0.01)) 
            for i in range(1, 51)
        }

    async def update_driver_coordinate(self, driver_id: str, lat: float, lon: float):
        self.driver_locations[driver_id] = (lat, lon)
        await heartbeat_service.update(driver_id)

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine formula approximation for distance between coordinates."""
        R = 3958.8 # Radius of the earth in miles
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (math.sin(d_lat / 2) ** 2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(d_lon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    async def find_optimal_driver(self, order_lat: float, order_lon: float) -> Optional[str]:
        """
        Finds the closest online driver who has an active heartbeat.
        """
        best_driver: Optional[str] = None
        min_distance = float('inf')

        for driver_id, (d_lat, d_lon) in self.driver_locations.items():
            # Check if driver is currently online via heartbeat service
            if await heartbeat_service.is_online(driver_id):
                distance = self._calculate_distance(order_lat, order_lon, d_lat, d_lon)
                if distance < min_distance:
                    min_distance = distance
                    best_driver = driver_id

        return best_driver

dispatch_service = DispatchService()
