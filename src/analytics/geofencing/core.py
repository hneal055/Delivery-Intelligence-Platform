from shapely.geometry import Point, Polygon
from src.backend.models.domain import Location

def is_in_delivery_zone(driver_loc: Location, delivery_zone: list[Location]) -> bool:
    """
    Determines if a driver's location falls within a delivery zone polygon.
    Safely handles malformed or insufficient zone coordinates.
    """
    if not delivery_zone or len(delivery_zone) < 3:
        return False

    point = Point(driver_loc.lon, driver_loc.lat)
    
    # Construct polygon from longitude/latitude pairs
    polygon = Polygon([(l.lon, l.lat) for l in delivery_zone])
    
    # Check validity to avoid topological errors with self-intersecting rings
    if not polygon.is_valid:
        polygon = polygon.buffer(0)  # Fix minor self-intersections if possible

    return polygon.contains(point)