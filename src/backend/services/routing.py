import math
import logging
from typing import List, Dict

logger = logging.getLogger("delivery_platform.routing")

class RouteOptimizer:
    @staticmethod
    def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        # Haversine formula approximation for distance in kilometers
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def optimize_route(self, start_coords: Tuple[float, float], stops: List[Dict]) -> List[Dict]:
        """Simple nearest-neighbor heuristic for stop sequencing."""
        unvisited = list(stops)
        optimized = []
        current_lat, current_lng = start_coords

        while unvisited:
            # Find nearest unvisited stop
            nearest = min(
                unvisited,
                key=lambda s: self.distance(current_lat, current_lng, s["lat"], s["lng"]) if "distance" in locals() else 0
            )
            # Better implementation using helper distance calculation:
            nearest = min(
                unvisited,
                key=lambda s: self.calculate_distance(current_lat, current_lng, s["lat"], s["lng"])
            )
            optimized.append(nearest)
            unvisited.remove(nearest)
            current_lat, current_lng = nearest["lat"], nearest["lng"]

        return optimized

route_optimizer = RouteOptimizer()
