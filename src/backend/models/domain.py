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
    priority: str = "standard"
    scheduled_window_start: Optional[datetime] = None
    scheduled_window_end: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class Driver(BaseModel):
    id: str
    name: str
    current_location: Optional[Location] = None
    vehicle_id: Optional[str] = None
    shift_start: Optional[datetime] = None
    shift_end: Optional[datetime] = None

    class Config:
        from_attributes = True

class TruckManifest(BaseModel):
    vehicle_id: str
    driver_id: str
    packages: List[Package] = []

# --- Security Models ---
class UserRole(str, Enum):
    DRIVER = "driver"
    MANAGER = "manager"
    ADMIN = "admin"

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    role: UserRole = UserRole.DRIVER

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: str
    is_active: bool = True
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

# --- Phase 2: Dispatch & Scheduling ---

class JobStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class JobType(str, Enum):
    DELIVERY = "delivery"
    PICKUP = "pickup"
    SERVICE = "service"
    EXCEPTION = "exception"

class DispatchJobCreate(BaseModel):
    driver_id: Optional[str] = None
    title: str
    type: JobType = JobType.DELIVERY
    priority: str = "medium"
    notes: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    package_id: Optional[str] = None

class DispatchJob(DispatchJobCreate):
    id: str
    status: str = "pending"
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class AvailabilityCreate(BaseModel):
    driver_id: str
    date: datetime
    is_available: bool
    start_time: Optional[str] = None
    end_time: Optional[str] = None

class LocationUpdate(BaseModel):
    lat: float
    lon: float
    speed: Optional[float] = None
    heading: Optional[float] = None
    battery_level: Optional[float] = None
    timestamp: Optional[datetime] = None

