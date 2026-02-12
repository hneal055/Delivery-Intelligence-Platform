from sqlalchemy import Column, String, Boolean, Float, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
import uuid

from src.backend.core.database import Base
from src.backend.models.domain import UserRole

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default=UserRole.DRIVER.value)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<User {self.username}>"

class Driver(Base):
    __tablename__ = "drivers"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    status = Column(String, default="active")
    vehicle_id = Column(String, nullable=True)
    shift_start = Column(DateTime(timezone=True), nullable=True)
    shift_end = Column(DateTime(timezone=True), nullable=True)
    
    # Current Location (Flattened from Location model)
    current_lat = Column(Float, nullable=True)
    current_lon = Column(Float, nullable=True)
    location = Column(Geometry('POINT', srid=4326), nullable=True)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    packages = relationship("Package", back_populates="driver")
    jobs = relationship("DispatchJob", back_populates="driver")
    availability = relationship("DriverAvailability", back_populates="driver")
    location_history = relationship("LocationHistory", back_populates="driver")

    def __repr__(self):
        return f"<Driver {self.name}>"

class Package(Base):
    __tablename__ = "packages"

    id = Column(String, primary_key=True, default=generate_uuid)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=True)
    vehicle_id = Column(String, nullable=True)
    
    # Destination
    dest_lat = Column(Float, nullable=False)
    dest_lon = Column(Float, nullable=False)
    dest_address = Column(String, nullable=True)
    destination_location = Column(Geometry('POINT', srid=4326), nullable=True)
    
    status = Column(String, default="pending")
    section = Column(String, nullable=True)
    
    # Phase 2: Scheduling
    priority = Column(String, default="standard")
    scheduled_window_start = Column(DateTime(timezone=True), nullable=True)
    scheduled_window_end = Column(DateTime(timezone=True), nullable=True)

    # Customer Tracking
    tracking_code = Column(String, unique=True, index=True, nullable=True)

    # ML Training Features
    distance_km = Column(Float, nullable=True)
    traffic_condition = Column(Float, nullable=True)
    predicted_eta_seconds = Column(Float, nullable=True)
    
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    driver = relationship("Driver", back_populates="packages")

    def __repr__(self):
        return f"<Package {self.id} -> {self.status}>"

class DispatchJob(Base):
    __tablename__ = "dispatch_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=True)
    title = Column(String, nullable=False)
    type = Column(String, default="delivery") # delivery, pickup, service
    status = Column(String, default="pending") # pending, assigned, in_progress, completed, cancelled
    
    priority = Column(String, default="medium")
    notes = Column(String, nullable=True)
    
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Linked Package (optional)
    package_id = Column(String, ForeignKey("packages.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    driver = relationship("Driver", back_populates="jobs")

class DriverAvailability(Base):
    __tablename__ = "driver_availability"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    is_available = Column(Boolean, default=True)
    start_time = Column(String, nullable=True) # "09:00"
    end_time = Column(String, nullable=True)   # "17:00"
    
    driver = relationship("Driver", back_populates="availability")

class LocationHistory(Base):
    __tablename__ = "location_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=False, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    location = Column(Geometry('POINT', srid=4326), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    speed = Column(Float, nullable=True)
    heading = Column(Float, nullable=True)
    battery_level = Column(Float, nullable=True)
    
    driver = relationship("Driver", back_populates="location_history")


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String, unique=True, nullable=False)
    platform = Column(String, default="android")  # ios, android, web
    created_at = Column(DateTime(timezone=True), server_default=func.now())
