"""Custom permission classes for the accounts app."""
import logging

from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import BasePermission

logger = logging.getLogger("securebid")


class IsEmailVerified(BasePermission):
    """Allow access only to authenticated, email-verified users (403 on failure)."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            raise PermissionDenied("Forbidden.")

        if not getattr(user, "is_email_verified", False):
            raise PermissionDenied("Forbidden.")

        return True


class IsEmailVerifiedSilent(BasePermission):
    """Allow access only to authenticated, email-verified users (404 on failure)."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            raise NotFound("Not found.")

        if not getattr(user, "is_email_verified", False):
            raise NotFound("Not found.")

        return True


class IsAdminUser(BasePermission):
    """Allow access only to staff/admin accounts (server-side is_staff)."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            raise NotFound("Not found.")

        if not getattr(user, "is_staff", False):
            logger.warning(
                "Admin access denied for non-staff user=%s ip=%s agent=%s path=%s",
                getattr(user, "email", None),
                request.META.get("REMOTE_ADDR"),
                request.META.get("HTTP_USER_AGENT", ""),
                request.path,
            )
            raise NotFound("Not found.")

        return True


class IsSuperUser(BasePermission):
    """Allow access only to superuser accounts (server-side is_superuser).

    Reserved for the most privileged operations — notably role management
    (granting/revoking staff) — so that the ability to change privileges is
    itself restricted to the top tier, not delegated to every staff member
    (least privilege). Returns 404 (not 403) so the endpoint's existence is not
    disclosed to lower-privileged users.
    """

    def has_permission(self, request, view):
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            raise NotFound("Not found.")

        if not getattr(user, "is_superuser", False):
            logger.warning(
                "Superuser access denied for user=%s ip=%s agent=%s path=%s",
                getattr(user, "email", None),
                request.META.get("REMOTE_ADDR"),
                request.META.get("HTTP_USER_AGENT", ""),
                request.path,
            )
            raise NotFound("Not found.")

        return True
