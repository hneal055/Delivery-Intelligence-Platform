from typing import Dict, List, Optional
from datetime import datetime
from src.backend.models.domain import Package, VehicleSection, TruckManifest

# In-memory mock database for Phase 2
_inventory_db: Dict[str, TruckManifest] = {}

class InventoryService:
    """
    Manages the loading and tracking of packages within vehicles.
    Implementation of Requirement 1.2.1
    """

    def create_manifest(self, vehicle_id: str, driver_id: str) -> TruckManifest:
        """Initialize a new truck load."""
        manifest = TruckManifest(vehicle_id=vehicle_id, driver_id=driver_id)
        _inventory_db[vehicle_id] = manifest
        return manifest

    def load_package(self, vehicle_id: str, package: Package, section: VehicleSection) -> TruckManifest:
        """
        Scans a package into a specific section of the truck.
        Updates status and timestamp.
        """
        if vehicle_id not in _inventory_db:
             # Auto-create for simplicity in dev, or raise error in prod
             raise ValueError(f"No active manifest for vehicle {vehicle_id}")
        
        manifest = _inventory_db[vehicle_id]
        
        # Update package state
        package.status = "loaded"
        package.section = section
        package.loaded_at = datetime.now()
        
        # Check if already loaded to avoid duplicates
        existing_index = next((i for i, p in enumerate(manifest.packages) if p.id == package.id), None)
        
        if existing_index is not None:
             manifest.packages[existing_index] = package
        else:
             manifest.packages.append(package)
             
        return manifest

    def get_truck_inventory(self, vehicle_id: str) -> List[Package]:
        """Returns the real-time inventory of the truck."""
        manifest = _inventory_db.get(vehicle_id)
        return manifest.packages if manifest else []

    def get_package_location(self, vehicle_id: str, package_id: str) -> Optional[VehicleSection]:
        """Fast lookup for where a package is inside the truck."""
        manifest = _inventory_db.get(vehicle_id)
        if not manifest:
            return None
            
        package = next((p for p in manifest.packages if p.id == package_id), None)
        return package.section if package else None

inventory_service = InventoryService()
