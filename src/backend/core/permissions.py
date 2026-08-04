from enum import Enum
from typing import Set, Dict
from src.backend.models.domain import UserRole

class Permission(str, Enum):
    # Driver Permissions
    VIEW_OWN_PROFILE = "view:own_profile"
    UPDATE_OWN_LOCATION = "update:own_location"
    VIEW_ASSIGNED_PACKAGES = "view:assigned_packages"
    UPDATE_PACKAGE_STATUS = "update:package_status"
    
    # Manager Permissions
    VIEW_ALL_DRIVERS = "view:all_drivers"
    VIEW_ALL_PACKAGES = "view:all_packages"
    MANAGE_JOBS = "manage:jobs"  # Create, Assign, Delete jobs
    VIEW_ANALYTICS = "view:analytics"
    MANAGE_EQUIPMENT = "manage:equipment"
    
    # Admin Permissions
    MANAGE_USERS = "manage:users"
    SYSTEM_CONFIG = "system:config"

# Role -> Permissions Mapping
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.DRIVER: {
        Permission.VIEW_OWN_PROFILE,
        Permission.UPDATE_OWN_LOCATION,
        Permission.VIEW_ASSIGNED_PACKAGES,
        Permission.UPDATE_PACKAGE_STATUS,
    },
    # Dispatchers run the job queue: create/assign/track jobs and read the
    # reports panel, but no equipment administration (see DISPATCHER_USER_MANUAL).
    # Strictly narrower than MANAGER.
    UserRole.DISPATCHER: {
        Permission.VIEW_OWN_PROFILE,
        Permission.VIEW_ALL_DRIVERS,
        Permission.VIEW_ALL_PACKAGES,
        Permission.MANAGE_JOBS,
        Permission.VIEW_ANALYTICS,
    },
    UserRole.MANAGER: {
        Permission.VIEW_OWN_PROFILE,
        Permission.VIEW_ALL_DRIVERS,
        Permission.VIEW_ALL_PACKAGES,
        Permission.MANAGE_JOBS,
        Permission.VIEW_ANALYTICS,
        Permission.MANAGE_EQUIPMENT,
    },
    UserRole.ADMIN: {
        # Admin has everything
        Permission.VIEW_OWN_PROFILE,
        Permission.UPDATE_OWN_LOCATION, # In case admin wants to test driver app
        Permission.VIEW_ASSIGNED_PACKAGES,
        Permission.UPDATE_PACKAGE_STATUS,
        Permission.VIEW_ALL_DRIVERS,
        Permission.VIEW_ALL_PACKAGES,
        Permission.MANAGE_JOBS,
        Permission.VIEW_ANALYTICS,
        Permission.MANAGE_EQUIPMENT,
        Permission.MANAGE_USERS,
        Permission.SYSTEM_CONFIG,
    }
}
