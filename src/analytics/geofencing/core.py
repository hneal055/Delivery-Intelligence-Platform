from shapely.geometry import Point, Polygon
from src.backend.models.domain import Location
from typing import List

def is_in_delivery_zone(driver_loc: Location, delivery_zone: List[Location]) -> bool:
    point = Point(driver_loc.lon, driver_loc.lat)
    polygon = Polygon([(l.lon, l.lat) for l in delivery_zone])
    return polygon.contains(point)
