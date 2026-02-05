from sqlalchemy import Column, String, Boolean, Float, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
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
    
    # Current Location (Flattened from Location model)
    current_lat = Column(Float, nullable=True)
    current_lon = Column(Float, nullable=True)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    packages = relationship("Package", back_populates="driver")

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
    
    status = Column(String, default="pending")
    section = Column(String, nullable=True)

    # ML Training Features
    distance_km = Column(Float, nullable=True)  # Snapshot of distance at assignment
    traffic_condition = Column(Float, nullable=True) # 0.0 to 1.0 snapshot
    predicted_eta_seconds = Column(Float, nullable=True) # Model prediction
    
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    driver = relationship("Driver", back_populates="packages")

    def __repr__(self):
        return f"<Package {self.id} -> {self.status}>"
