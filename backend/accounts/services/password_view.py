"""Password reset + change API (diagram: svc_password)."""
import logging
import time

from axes.utils import reset
from django.contrib.auth.signals import user_login_failed
from django.core.mail import BadHeaderError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.cross_cutting.audit import log_action, device_fingerprint as _device_fingerprint

from ..business.emails import send_password_reset_email
from ..business.password import is_password_breached
from ..business.session_manager import (
    get_client_ip,
    invalidate_all_user_sessions,
    normalise_auth_response_timing,
)
from ..business.tokens import consume_token, generate_password_reset_token, validate_token
from ..data.models import AccountLockoutProfile, PasswordResetToken
from .permissions import IsEmailVerified
from .serializers import PasswordResetConfirmSerializer, PasswordResetRequestSerializer

logger = logging.getLogger("securebid")


class PasswordResetRequestView(APIView):
    """Request a password reset link."""

    permission_classes = [AllowAny]

    def post(self, request):
        start_time = time.perf_counter()

        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        found_user = None

        from django.contrib.auth import get_user_model

        User = get_user_model()

        try:
            found_user = User.objects.get(
                email=email, is_active=True, is_email_verified=True
            )
            raw_token = generate_password_reset_token(found_user)
            send_password_reset_email(found_user, raw_token)
        except User.DoesNotExist:
            pass  # Respond identically — no account enumeration.
        except (BadHeaderError, OSError) as exc:
            logger.error("Failed to send password reset email to %s: %s", email, exc)

        # Log the attempt regardless of whether the account exists (NFSR-AC-02).
        try:
            log_action(
                user=found_user,
                action="password_reset_requested",
                resource_type="User",
                resource_id=found_user.id if found_user else None,
                ip_address=ip,
                user_agent=ua,
                device_fingerprint=_device_fingerprint(ip, ua),
                role="user" if found_user else "anonymous",
                request_method=request.method,
                endpoint_path=request.path,
                metadata={"email_submitted": email},
            )
        except Exception:
            pass

        normalise_auth_response_timing(start_time)
        return Response(
            {
                "detail": "If an account with that email exists, a password reset "
                "link has been sent. Please check your inbox."
            },
            status=200,
        )


class PasswordResetConfirmView(APIView):
    """Confirm a password reset using a one-time token."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_string = serializer.validated_data["token"]
        password = serializer.validated_data["password"]

        record = validate_token(token_string, PasswordResetToken)
        if record is None or not consume_token(record):
            return Response(
                {
                    "detail": "This reset link is invalid or has expired. "
                    "Please request a new one."
                },
                status=400,
            )

        user = record.user
        user.set_password(password)
        user.save(update_fields=["password"])

        # Reset custom escalating lockout profile only after successful password reset.
        AccountLockoutProfile.objects.update_or_create(
            user=user,
            defaults={
                "lockout_level": 0,
                "locked_until": None,
                "last_lockout_ip": None,
                "last_lockout_at": None,
            },
        )

        # Reset django-axes failed login attempts for this account.
        reset(username=user.email)

        # Invalidate all active sessions across all devices.
        invalidate_all_user_sessions(user)

        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        log_action(
            user=user,
            action="password_reset_confirmed",
            resource_type="User",
            resource_id=user.id,
            ip_address=ip,
            user_agent=ua,
            device_fingerprint=_device_fingerprint(ip, ua),
            role="staff" if user.is_staff else "user",
            request_method=request.method,
            endpoint_path=request.path,
            metadata={"email": user.email},
        )

        return Response(
            {"detail": "Password updated. You can now sign in."},
            status=200,
        )


class PasswordChangeView(APIView):
    """Allow an authenticated user to change their password."""

    permission_classes = [IsEmailVerified]

    def post(self, request):
        current_password = request.data.get("current_password", "")
        new_password = request.data.get("new_password", "")

        if not current_password or not new_password:
            return Response(
                {"detail": "Current password and new password are required."},
                status=400,
            )

        if not request.user.check_password(current_password):
            user_login_failed.send(
                sender=request.user.__class__,
                credentials={"username": request.user.email},
                request=request,
            )
            return Response({"detail": "Current password is incorrect."}, status=400)

        if len(new_password) < 12 or len(new_password) > 128:
            return Response(
                {"detail": "New password must be between 12 and 128 characters."},
                status=400,
            )

        if is_password_breached(new_password):
            return Response(
                {
                    "detail": "This password has appeared in a known data breach. "
                    "Please choose a different one."
                },
                status=400,
            )

        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])

        # Flush current session properly so Django's session middleware does not
        # error trying to save a deleted session row, then clear all other devices.
        request.session.flush()
        invalidate_all_user_sessions(request.user)

        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        log_action(
            user=request.user,
            action="password_changed",
            resource_type="User",
            resource_id=request.user.id,
            ip_address=ip,
            user_agent=ua,
            device_fingerprint=_device_fingerprint(ip, ua),
            role="staff" if request.user.is_staff else "user",
            request_method=request.method,
            endpoint_path=request.path,
            metadata={"email": request.user.email},
        )

        return Response(
            {"detail": "Password changed successfully. Please sign in again."},
            status=200,
        )
