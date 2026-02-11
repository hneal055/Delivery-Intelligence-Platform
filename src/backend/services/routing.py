from typing import List, Optional
from src.backend.models.domain import Location
from src.backend.services.mapbox import mapbox_service
import math
import logging

logger = logging.getLogger(__name__)


class RoutingService:
    """
    Route optimization with Mapbox integration.
    Uses Mapbox distance matrix when available, falls back to haversine + 2-Opt.
    """

    async def optimize_route_mapbox(self, start_location: Location, stops: List[Location]) -> Optional[List[Location]]:
        """
        Optimize route using Mapbox travel-time matrix.
        Returns None if Mapbox is unavailable.
        """
        if not mapbox_service.enabled or not stops:
            return None

        all_points = [start_location] + stops
        coordinates = [(loc.lat, loc.lon) for loc in all_points]

        matrix = await mapbox_service.get_distance_matrix(coordinates)
        if not matrix or not matrix.get("durations"):
            return None

        durations = matrix["durations"]

        # Nearest-neighbor using travel times
        visited = {0}
        route_indices = [0]
        current = 0

        while len(visited) < len(all_points):
            best_next = None
            best_time = float("inf")
            for j in range(len(all_points)):
                if j not in visited and durations[current][j] is not None:
                    if durations[current][j] < best_time:
                        best_time = durations[current][j]
                        best_next = j
            if best_next is None:
                break
            visited.add(best_next)
            route_indices.append(best_next)
            current = best_next

        # Return stops only (exclude start)
        return [all_points[i] for i in route_indices[1:]]

    def optimize_route(self, start_location: Location, stops: List[Location]) -> List[Location]:
        """
        Haversine-based optimization with Nearest Neighbor + 2-Opt.
        Used as fallback when Mapbox is unavailable.
        """
        if not stops:
            return []

        greedy_route = [start_location]
        remaining_nodes = stops.copy()
        current_node = start_location

        while remaining_nodes:
            next_stop = min(
                remaining_nodes,
                key=lambda loc: self._haversine_distance(current_node, loc)
            )
            greedy_route.append(next_stop)
            remaining_nodes.remove(next_stop)
            current_node = next_stop

        optimized_full_route = self._two_opt(greedy_route)
        return optimized_full_route[1:]

    def _two_opt(self, route: List[Location]) -> List[Location]:
        best_route = route[:]
        improved = True
        max_iterations = 100
        iteration = 0

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            for i in range(1, len(best_route) - 1):
                for j in range(i + 1, len(best_route) + 1):
                    if j - i == 1:
                        continue
                    new_route = best_route[:]
                    new_route[i:j] = best_route[i:j][::-1]
                    if self._calculate_total_distance(new_route) < self._calculate_total_distance(best_route):
                        best_route = new_route
                        improved = True
        return best_route

    def _calculate_total_distance(self, route: List[Location]) -> float:
        total = 0.0
        for i in range(len(route) - 1):
            total += self._haversine_distance(route[i], route[i + 1])
        return total

    def _haversine_distance(self, loc1: Location, loc2: Location) -> float:
        R = 6371e3
        phi1 = math.radians(loc1.lat)
        phi2 = math.radians(loc2.lat)
        dphi = math.radians(loc2.lat - loc1.lat)
        dlambda = math.radians(loc2.lon - loc1.lon)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c


routing_service = RoutingService()
