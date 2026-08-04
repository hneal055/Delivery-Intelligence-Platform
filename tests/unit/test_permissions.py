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

    def test_dispatcher_can_manage_jobs(self):
        assert Permission.MANAGE_JOBS in ROLE_PERMISSIONS[UserRole.DISPATCHER]

    def test_dispatcher_can_view_drivers_and_packages(self):
        """Assigning drivers to jobs requires seeing both."""
        dispatcher_perms = ROLE_PERMISSIONS[UserRole.DISPATCHER]
        assert Permission.VIEW_ALL_DRIVERS in dispatcher_perms
        assert Permission.VIEW_ALL_PACKAGES in dispatcher_perms

    def test_dispatcher_cannot_manage_equipment_or_users(self):
        dispatcher_perms = ROLE_PERMISSIONS[UserRole.DISPATCHER]
        assert Permission.MANAGE_EQUIPMENT not in dispatcher_perms
        assert Permission.MANAGE_USERS not in dispatcher_perms

    def test_dispatcher_permissions_are_strict_subset_of_manager(self):
        dispatcher_perms = ROLE_PERMISSIONS[UserRole.DISPATCHER]
        manager_perms = ROLE_PERMISSIONS[UserRole.MANAGER]
        assert dispatcher_perms < manager_perms

    def test_every_role_has_a_permission_set(self):
        """A role missing from ROLE_PERMISSIONS is silently denied everything."""
        for role in UserRole:
            assert role in ROLE_PERMISSIONS, f"Role has no permissions: {role}"
            assert ROLE_PERMISSIONS[role], f"Role has empty permissions: {role}"

    def test_update_own_location_only_for_driver_and_admin(self):
        """Managers should not update driver locations on behalf of drivers."""
        assert Permission.UPDATE_OWN_LOCATION not in ROLE_PERMISSIONS[UserRole.MANAGER]
        assert Permission.UPDATE_OWN_LOCATION in ROLE_PERMISSIONS[UserRole.DRIVER]
        assert Permission.UPDATE_OWN_LOCATION in ROLE_PERMISSIONS[UserRole.ADMIN]
