"""Admin user list/detail API (diagram: svc_admin_users)."""
import logging

from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.views import APIView

from core.cross_cutting.audit import log_action, device_fingerprint as _device_fingerprint

from ..business.session_manager import get_client_ip
from ..business.session_termination_service import terminate_user_sessions
from ..business.user_management_service import get_admin_target, toggle_account_active
from .permissions import IsAdminUser
from .serializers import AdminUserListSerializer

logger = logging.getLogger("securebid")

User = get_user_model()


class AdminUserListView(APIView):
    """Return all user accounts for the admin panel (staff only)."""

    permission_classes = [IsAdminUser]
    staff_only = True

    def get(self, request):
        qs = User.objects.filter(is_anonymised=False).order_by("-created_at")
        serializer = AdminUserListSerializer(qs, many=True)
        return Response(serializer.data)


class AdminUserDetailView(APIView):
    """Lock/unlock or delete a single user account (staff only).

    Guards:
    - Cannot act on your own account.
    - Cannot act on a superuser account (superusers are managed via Django shell).
    """

    permission_classes = [IsAdminUser]
    staff_only = True
    http_method_names = ["patch", "delete"]

    def patch(self, request, user_id):
        """Toggle is_active (lock / unlock)."""
        target, err = get_admin_target(request, user_id)
        if err:
            return err

        is_active = toggle_account_active(target)
        action = "unlocked" if is_active else "locked"
        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        log_action(
            user=request.user,
            action="admin_account_toggled",
            resource_type="User",
            resource_id=target.id,
            ip_address=ip,
            user_agent=ua,
            device_fingerprint=_device_fingerprint(ip, ua),
            role="staff" if request.user.is_staff else "user",
            request_method=request.method,
            endpoint_path=request.path,
            metadata={"target_email": target.email, "action": action},
        )
        logger.info("Admin %s %s account %s", request.user.email, action, target.email)
        return Response({"detail": f"Account {action}.", "is_active": is_active})

    def delete(self, request, user_id):
        """Permanently delete a user account."""
        from ..business.anonymisation import anonymise_user_data

        target, err = get_admin_target(request, user_id)
        if err:
            return err

        email = target.email
        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        log_action(
            user=request.user,
            action="admin_account_deleted",
            resource_type="User",
            resource_id=target.id,
            ip_address=ip,
            user_agent=ua,
            device_fingerprint=_device_fingerprint(ip, ua),
            role="staff" if request.user.is_staff else "user",
            request_method=request.method,
            endpoint_path=request.path,
            metadata={"target_email": email},
        )
        # Soft-delete: anonymise PII in-place (NFSR-C-08 · SFR-05c).
        terminate_user_sessions(target)
        anonymise_user_data(target)
        logger.info("Admin %s deleted and anonymised account %s", request.user.email, email)
        return Response({"detail": "Account deleted."}, status=200)
