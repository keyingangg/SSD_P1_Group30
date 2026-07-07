"""Terminate sessions API (diagram: svc_terminate)."""
import logging

from rest_framework.response import Response
from rest_framework.views import APIView

from core.cross_cutting.audit import log_action, device_fingerprint as _device_fingerprint

from ..business.session_manager import get_client_ip
from ..business.session_termination_service import terminate_user_sessions
from ..business.user_management_service import get_admin_target
from .permissions import IsAdminUser

logger = logging.getLogger("securebid")


class AdminTerminateSessionsView(APIView):
    """Kill a user's live session(s) without locking or deleting the account (FSR-C-07)."""

    permission_classes = [IsAdminUser]
    staff_only = True
    http_method_names = ["post"]

    def post(self, request, user_id):
        target, err = get_admin_target(request, user_id)
        if err:
            return err

        terminate_user_sessions(target)
        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        log_action(
            user=request.user,
            action="admin_session_terminated",
            resource_type="User",
            resource_id=target.id,
            ip_address=ip,
            user_agent=ua,
            device_fingerprint=_device_fingerprint(ip, ua),
            role="staff" if request.user.is_staff else "user",
            request_method=request.method,
            endpoint_path=request.path,
            metadata={"target_email": target.email},
        )
        logger.info("Admin %s terminated sessions for %s", request.user.email, target.email)
        return Response({"detail": "Sessions terminated."}, status=200)
