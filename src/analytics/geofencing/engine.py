from typing import List, Optional
from shapely.geometry import Point, Polygon
from src.backend.models.domain import Location
import math

class GeofenceEngine:
    """
    Advanced geofencing and spatial analysis for delivery tracking.
    Implementation of Requirement 1.2.2
    """

    def is_in_zone(self, driver_loc: Location, zone_polygon: List[Location]) -> bool:
        """
        Determines if a driver is physically inside a defined delivery zone.
        Uses Shapely for precise point-in-polygon calculation.
        """
        if len(zone_polygon) < 3:
            # A polygon must have at least 3 points
            return False 
        
        # Shapely uses (x, y) which maps to (lon, lat)
        point = Point(driver_loc.lon, driver_loc.lat)
        poly = Polygon([(p.lon, p.lat) for p in zone_polygon])
        
        return poly.contains(point)

    def calculate_distance_meters(self, loc1: Location, loc2: Location) -> float:
        """
        Haversine formula to calculate Great Circle distance between two points in meters.
        """
        R = 6371000  # Radius of Earth in meters
        phi1 = math.radians(loc1.lat)
        phi2 = math.radians(loc2.lat)
        delta_phi = math.radians(loc2.lat - loc1.lat)
        delta_lambda = math.radians(loc2.lon - loc1.lon)

        a = math.sin(delta_phi / 2.0) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda / 2.0) ** 2
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return round(R * c, 2)

    def estimate_eta_minutes(self, driver_loc: Location, dest_loc: Location, avg_speed_kmh: float = 30.0) -> float:
        """
        Estimates time of arrival based on straight-line distance and average city speed.
        In a real production environment, this would call a routing API (e.g., OSRM, Google Maps).
        
        :param avg_speed_kmh: Default city driving speed (30 km/h)
        """
        dist_meters = self.calculate_distance_meters(driver_loc, dest_loc)
        speed_mps = avg_speed_kmh * (1000.0 / 3600.0) # Convert km/h to m/s
        
        if speed_mps <= 0:
            return float('inf')
            
        seconds = dist_meters / speed_mps
        return round(seconds / 60.0, 1)

    def create_circular_zone(self, center: Location, radius_meters: float) -> List[Location]:
        """
        Helper to generate a Polygon approximation of a circle (buffer) around a point.
        Useful for creating default delivery zones around an address.
        """
        center_point = Point(center.lon, center.lat)
        # 1 degree lat ~= 111,000 meters. 
        # This is a rough flat-earth approximation for small buffers.
        buffer_deg = radius_meters / 111320.0 
        
        circle_poly = center_point.buffer(buffer_deg)
        
        # Convert back to Locations
        coords = list(circle_poly.exterior.coords)
        return [Location(lon=c[0], lat=c[1]) for c in coords]

geofence_engine = GeofenceEngine()
