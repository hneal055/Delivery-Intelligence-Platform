from typing import List
from src.backend.models.domain import Location
import math

class RoutingService:
    """
    Service responsible for route optimization.
    Phase 3.1 Implementation.
    """

    def optimize_route(self, start_location: Location, stops: List[Location]) -> List[Location]:
        """
        Mock implementation of a Traveling Salesperson Problem (TSP) solver.
        In production, this would use OR-Tools or distinct routing APIs.
        
        Current Mock Logic:
        Sorts locations by nearest neighbor (greedy algorithm) starting from current location.
        """
        if not stops:
            return []

        optimized_route = []
        current_node = start_location
        remaining_nodes = stops.copy()

        while remaining_nodes:
            # Find the closest next stop
            next_stop = min(
                remaining_nodes,
                key=lambda loc: self._simple_distance_score(current_node, loc)
            )
            
            optimized_route.append(next_stop)
            remaining_nodes.remove(next_stop)
            current_node = next_stop

        return optimized_route

    def _simple_distance_score(self, loc1: Location, loc2: Location) -> float:
        """Euclidean distance approximation for sorting (fast)."""
        return math.sqrt((loc1.lat - loc2.lat)**2 + (loc1.lon - loc2.lon)**2)

routing_service = RoutingService()
