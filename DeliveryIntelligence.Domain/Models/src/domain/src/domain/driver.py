from enum import Enum
from pydantic import BaseModel


class DriverStatus(str, Enum):
    OFFLINE = "OFFLINE"
    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    EN_ROUTE_PICKUP = "EN_ROUTE_PICKUP"
    AT_PICKUP = "AT_PICKUP"
    EN_ROUTE_DELIVERY = "EN_ROUTE_DELIVERY"
    AT_DELIVERY = "AT_DELIVERY"
    BREAK = "BREAK"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class Driver(BaseModel):
    driver_id: str
    first_name: str
    last_name: str

    status: DriverStatus

    vehicle_id: str | None = None