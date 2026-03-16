"""
Unit tests for the RBAC permissions system.
Pure-logic tests — no DB or network required.
"""
import pytest
from src.backend.core.permissions import ROLE_PERMISSIONS, Permission
from src.backend.models.domain import UserRole


class TestRolePermissions:
    def test_driver_can_view_own_profile(self):
        assert Permission.VIEW_OWN_PROFILE in ROLE_PERMISSIONS[UserRole.DRIVER]

    def test_driver_cannot_view_all_drivers(self):
        assert Permission.VIEW_ALL_DRIVERS not in ROLE_PERMISSIONS[UserRole.DRIVER]

    def test_driver_cannot_manage_users(self):
        assert Permission.MANAGE_USERS not in ROLE_PERMISSIONS[UserRole.DRIVER]

    def test_manager_can_manage_jobs(self):
        assert Permission.MANAGE_JOBS in ROLE_PERMISSIONS[UserRole.MANAGER]

    def test_manager_cannot_manage_users(self):
        assert Permission.MANAGE_USERS not in ROLE_PERMISSIONS[UserRole.MANAGER]

    def test_admin_has_all_permissions(self):
        admin_perms = ROLE_PERMISSIONS[UserRole.ADMIN]
        for perm in Permission:
            assert perm in admin_perms, f"Admin missing permission: {perm}"

    def test_driver_permissions_are_subset_of_admin(self):
        driver_perms = ROLE_PERMISSIONS[UserRole.DRIVER]
        admin_perms = ROLE_PERMISSIONS[UserRole.ADMIN]
        assert driver_perms.issubset(admin_perms)

    def test_manager_permissions_are_subset_of_admin(self):
        manager_perms = ROLE_PERMISSIONS[UserRole.MANAGER]
        admin_perms = ROLE_PERMISSIONS[UserRole.ADMIN]
        assert manager_perms.issubset(admin_perms)

    def test_driver_and_manager_have_different_permissions(self):
        driver_perms = ROLE_PERMISSIONS[UserRole.DRIVER]
        manager_perms = ROLE_PERMISSIONS[UserRole.MANAGER]
        assert driver_perms != manager_perms

    def test_update_own_location_only_for_driver_and_admin(self):
        """Managers should not update driver locations on behalf of drivers."""
        assert Permission.UPDATE_OWN_LOCATION not in ROLE_PERMISSIONS[UserRole.MANAGER]
        assert Permission.UPDATE_OWN_LOCATION in ROLE_PERMISSIONS[UserRole.DRIVER]
        assert Permission.UPDATE_OWN_LOCATION in ROLE_PERMISSIONS[UserRole.ADMIN]
