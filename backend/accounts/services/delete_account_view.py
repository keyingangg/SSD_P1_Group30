"""Self-service account deletion API (diagram: svc_delete)."""
import logging

from django.contrib.auth.signals import user_login_failed
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.cross_cutting.audit import log_action, device_fingerprint as _device_fingerprint

from ..business.anonymisation import anonymise_user_data
from ..business.session_manager import get_client_ip, invalidate_all_user_sessions

logger = logging.getLogger("securebid")


class DeleteAccountView(APIView):
    """Permanently delete the authenticated user's account (SFR-05a).

    If MFA is enrolled, a valid TOTP code must be supplied in the request body.
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["post"]

    def post(self, request):
        user = request.user

        # Admin accounts must be deleted by another admin, not by themselves.
        if user.is_staff or user.is_superuser:
            return Response(
                {"detail": "Admin accounts cannot be self-deleted. Contact another administrator."},
                status=403,
            )

        # Step 1: require current password re-entry (SFR-05a).
        current_password = request.data.get("current_password", "")
        if not current_password:
            return Response(
                {"detail": "Your current password is required to delete your account."},
                status=400,
            )
        if not user.check_password(current_password):
            user_login_failed.send(
                sender=user.__class__,
                credentials={"username": user.email},
                request=request,
            )
            return Response({"detail": "Invalid password."}, status=400)

        # Step 2: if MFA is enrolled, also require a valid TOTP code (SFR-05a).
        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        if device:
            otp_code = request.data.get("otp_code", "").replace(" ", "")
            if not otp_code:
                return Response(
                    {"detail": "MFA verification required.", "mfa_required": True},
                    status=403,
                )
            if not device.verify_token(otp_code):
                user_login_failed.send(
                    sender=user.__class__,
                    credentials={"username": user.email},
                    request=request,
                )
                return Response({"detail": "Invalid MFA code."}, status=400)

        # Step 3: block deletion while an unpaid winning bid exists (SFR-05b) —
        # otherwise the seller is left with no way to collect payment.
        from payments.data.models import Order

        if Order.objects.filter(winner_id=user.id, fulfillment_status="pending_payment").exists():
            return Response(
                {"detail": "You have an outstanding unpaid order. Please complete or cancel payment before deleting your account."},
                status=400,
            )

        email = user.email
        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        # Flush the current session and invalidate all other active sessions
        # before deletion so the session middleware finds nothing to save after
        # the user row is gone.
        request.session.flush()
        invalidate_all_user_sessions(user)
        log_action(
            user=user,
            action="account_deleted",
            resource_type="User",
            resource_id=user.id,
            ip_address=ip,
            user_agent=ua,
            device_fingerprint=_device_fingerprint(ip, ua),
            role="staff" if user.is_staff else "user",
            request_method=request.method,
            endpoint_path=request.path,
            metadata={"email": email},
        )
        # Soft-delete: anonymise PII in-place rather than hard-deleting.
        # Preserves auction integrity (bids, orders) and audit trail continuity
        # while satisfying PDPA right-to-erasure within 30 days (NFSR-C-08).
        anonymise_user_data(user)
        logger.info("User %s deleted and anonymised their account", email)
        return Response({"detail": "Your account has been deleted."}, status=200)
