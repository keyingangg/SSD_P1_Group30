"""Staff invite + accept-invite API (diagram: svc_invite)."""
import logging
import smtplib

from django.contrib.auth import get_user_model
from django.core.mail import BadHeaderError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.cross_cutting.audit import log_action, device_fingerprint as _device_fingerprint

from ..business.session_manager import get_client_ip
from ..business.staff_invite_service import accept_staff_invite, create_staff_invite
from .permissions import IsSuperUser
from .serializers import AcceptInviteSerializer, StaffInviteSerializer

logger = logging.getLogger("securebid")

User = get_user_model()


class StaffInviteView(APIView):
    """Send a staff invitation to a new admin team member (admin only).

    Creates an inactive staff account with an unusable password so the
    inviting admin never handles a credential. The invitee sets their own
    password when they accept the link.

    Restricted to superusers: granting staff privileges is a top-tier operation
    reserved for the owner account, not delegated to every staff member.
    """

    permission_classes = [IsSuperUser]
    staff_only = True

    def post(self, request):
        serializer = StaffInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        if User.objects.filter(email=email).exists():
            return Response(
                {"detail": "An account with that email already exists."},
                status=400,
            )

        user = None
        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        try:
            user = create_staff_invite(email, invited_by=request.user)

            # Log admin role promotion (NFSR-AC-02).
            log_action(
                user=request.user,
                action="admin_role_promoted",
                resource_type="User",
                resource_id=user.id,
                ip_address=ip,
                user_agent=ua,
                device_fingerprint=_device_fingerprint(ip, ua),
                role="staff" if request.user.is_staff else "user",
                request_method=request.method,
                endpoint_path=request.path,
                metadata={
                    "invited_email": email,
                    "invited_by": request.user.email,
                    "new_role": "staff",
                },
            )
        except (BadHeaderError, smtplib.SMTPException, OSError) as exc:
            logger.error("Failed to send staff invite to %s: %s", email, exc)
            if user is not None:
                user.delete()
            return Response(
                {"detail": "Could not send the invitation email. Please try again."},
                status=503,
            )

        return Response(
            {"detail": f"Invitation sent to {email}."},
            status=201,
        )


class AcceptInviteView(APIView):
    """Accept a staff invitation: set display name and password."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AcceptInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_string = serializer.validated_data["token"]
        display_name = serializer.validated_data["display_name"]
        password = serializer.validated_data["password"]

        user = accept_staff_invite(token_string, display_name, password)
        if user is None:
            return Response(
                {
                    "detail": "This invitation link is invalid or has expired. "
                    "Please ask an admin to resend it."
                },
                status=400,
            )

        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        try:
            log_action(
                user=user,
                action="staff_account_activated",
                resource_type="User",
                resource_id=user.id,
                ip_address=ip,
                user_agent=ua,
                device_fingerprint=_device_fingerprint(ip, ua),
                role="staff",
                request_method=request.method,
                endpoint_path=request.path,
                metadata={"email": user.email},
            )
        except Exception:
            pass

        return Response(
            {"detail": "Account set up successfully. You can now sign in."},
            status=200,
        )
