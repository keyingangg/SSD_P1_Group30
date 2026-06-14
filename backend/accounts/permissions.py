"""Custom permission classes for the accounts app."""
from rest_framework.permissions import BasePermission


class IsEmailVerified(BasePermission):
    """Allow access only to authenticated, email-verified users."""

    def has_permission(self, request, view):
        # TODO: return request.user.is_authenticated and is_email_verified.
        return False


class IsAdminUser(BasePermission):
    """Allow access only to staff/admin accounts (server-side is_staff)."""

    def has_permission(self, request, view):
        # TODO: return request.user.is_authenticated and request.user.is_staff.
        return False
