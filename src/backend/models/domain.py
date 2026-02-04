from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class Location(BaseModel):
    lat: float
    lon: float
    address: Optional[str] = None

class VehicleSection(str, Enum):
    FRONT_LEFT = "Front-Left"
    FRONT_RIGHT = "Front-Right"
    MIDDLE_LEFT = "Middle-Left"
    MIDDLE_RIGHT = "Middle-Right"
    REAR = "Rear"

class Package(BaseModel):
    id: str
    destination: Location
    status: str = "pending"
    loaded_at: Optional[datetime] = None
    section: Optional[VehicleSection] = None

class Driver(BaseModel):
    id: str
    name: str
    current_location: Optional[Location] = None

class TruckManifest(BaseModel):
    vehicle_id: str
    driver_id: str
    packages: List[Package] = []
