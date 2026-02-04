from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Location(BaseModel):
    lat: float
    lon: float
    address: Optional[str] = None

class Package(BaseModel):
    id: str
    destination: Location
    status: str = "pending"

class Driver(BaseModel):
    id: str
    name: str
    current_location: Optional[Location] = None
