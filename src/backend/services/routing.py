from typing import List
from src.backend.models.domain import Location
import math

class RoutingService:
    """
    Service responsible for route optimization.
    Phase 9 Implementation: Advanced Routing (2-Opt Local Search + Haversine).
    """

    def optimize_route(self, start_location: Location, stops: List[Location]) -> List[Location]:
        """
        Optimizes the route using Nearest Neighbor initialization followed by 2-Opt optimization.
        """
        if not stops:
            return []

        # 1. Greedy Initialization (Nearest Neighbor)
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

        # 2. 2-Opt Improvement
        optimized_full_route = self._two_opt(greedy_route)

        # Remove the start_location
        return optimized_full_route[1:]

    def _two_opt(self, route: List[Location]) -> List[Location]:
        """
        Iteratively reverse segments to reduce total distance.
        Keeps the start point (index 0) fixed.
        """
        best_route = route[:]
        improved = True
        max_iterations = 100 
        iteration = 0

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            # Fix range to allow swapping up to the end of the list
            for i in range(1, len(best_route) - 1):
                for j in range(i + 1, len(best_route) + 1):
                    if j - i == 1: continue 
                    
                    new_route = best_route[:]
                    new_route[i:j] = best_route[i:j][::-1]
                    
                    if self._calculate_total_distance(new_route) < self._calculate_total_distance(best_route):
                        best_route = new_route
                        improved = True
        
        return best_route

    def _calculate_total_distance(self, route: List[Location]) -> float:
        total = 0.0
        for i in range(len(route) - 1):
            total += self._haversine_distance(route[i], route[i+1])
        return total

    def _haversine_distance(self, loc1: Location, loc2: Location) -> float:
        R = 6371e3 
        phi1 = math.radians(loc1.lat)
        phi2 = math.radians(loc2.lat)
        dphi = math.radians(loc2.lat - loc1.lat)
        dlambda = math.radians(loc2.lon - loc1.lon)

        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

routing_service = RoutingService()
