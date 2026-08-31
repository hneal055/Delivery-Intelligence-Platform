import math
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def haversine_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in miles."""
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_total_route_distance(origin: Dict[str, float], stops: List[Dict[str, Any]]) -> float:
    """Calculates total mileage along an ordered sequence of stops."""
    if not stops:
        return 0.0
    total = haversine_distance_miles(origin["lat"], origin["lon"], stops[0]["lat"], stops[0]["lon"])
    for i in range(len(stops) - 1):
        total += haversine_distance_miles(stops[i]["lat"], stops[i]["lon"], stops[i+1]["lat"], stops[i+1]["lon"])
    return round(total, 2)

def optimize_stop_sequence(current_lat: float, current_lon: float, stops: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Applies Nearest Neighbor heuristic followed by 2-Opt local search
    to find the optimal stop sequence.
    """
    if not stops:
        return {"optimized_stops": [], "original_distance_miles": 0.0, "optimized_distance_miles": 0.0, "savings_percent": 0.0}

    origin = {"lat": current_lat, "lon": current_lon}
    original_dist = calculate_total_route_distance(origin, stops)

    # 1. Nearest Neighbor Initialization
    unvisited = list(stops)
    ordered_stops = []
    curr_pos = origin

    while unvisited:
        nearest_idx = 0
        min_dist = float("inf")
        for idx, stop in enumerate(unvisited):
            dist = haversine_distance_miles(curr_pos["lat"], curr_pos["lon"], stop["lat"], stop["lon"])
            if dist < min_dist:
                min_dist = dist
                nearest_idx = idx
        
        next_stop = unvisited.pop(nearest_idx)
        ordered_stops.append(next_stop)
        curr_pos = {"lat": next_stop["lat"], "lon": next_stop["lon"]}

    # 2. 2-Opt Refinement Loop
    improved = True
    iteration = 0
    max_iterations = 20

    while improved and iteration < max_iterations:
        improved = False
        iteration += 1
        for i in range(len(ordered_stops) - 1):
            for j in range(i + 2, len(ordered_stops) + 1):
                new_route = ordered_stops[:i] + ordered_stops[i:j][::-1] + ordered_stops[j:]
                if calculate_total_route_distance(origin, new_route) < calculate_total_route_distance(origin, ordered_stops):
                    ordered_stops = new_route
                    improved = True
                    break
            if improved:
                break

    optimized_dist = calculate_total_route_distance(origin, ordered_stops)
    savings = round(((original_dist - optimized_dist) / (original_dist or 1.0)) * 100, 1) if original_dist > 0 else 0.0

    # Assign sequential stop order index
    for idx, stop in enumerate(ordered_stops):
        stop["sequence_index"] = idx + 1

    return {
        "driver_origin": origin,
        "original_distance_miles": original_dist,
        "optimized_distance_miles": optimized_dist,
        "savings_percent": max(0.0, savings),
        "total_stops": len(ordered_stops),
        "optimized_stops": ordered_stops,
    }
