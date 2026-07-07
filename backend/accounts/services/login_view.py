"""Login + logout API (diagram: svc_login)."""
import logging
import time

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.core.exceptions import PermissionDenied
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.cross_cutting.audit import log_action, device_fingerprint as _device_fingerprint

from ..business.auth_backend import clear_expired_lockout
from ..business.session_manager import (
    get_client_ip,
    normalise_auth_response_timing,
    notify_new_device_or_location,
)
from .serializers import UserLoginSerializer, UserProfileSerializer

logger = logging.getLogger("securebid")

User = get_user_model()

# Uniform response used for every failed login outcome to prevent account
# enumeration (NFSR-AU-05).
AUTH_FAILURE_RESPONSE = {
    "detail": "Invalid credentials or account not found."
}


@method_decorator(
    ratelimit(key="ip", rate="10/m", method="POST", block=True),
    name="post",
)
class LoginView(APIView):
    """Authenticate a verified user and start a session."""

    permission_classes = [AllowAny]
    http_method_names = ["post"]

    def post(self, request):
        start_time = time.perf_counter()

        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")

        # django-axes wraps authenticate(); a locked account raises
        # PermissionDenied. Unverified accounts are inactive, so authenticate()
        # returns None for them -> the same generic error (no enumeration).
        try:
            clear_expired_lockout(email)
            user = authenticate(request, username=email, email=email, password=password)
        except PermissionDenied:
            try:
                log_action(
                    user=None,
                    action="login_failed",
                    resource_type="User",
                    ip_address=ip,
                    user_agent=ua,
                    device_fingerprint=_device_fingerprint(ip, ua),
                    request_method=request.method,
                    endpoint_path=request.path,
                    metadata={"reason": "account_locked"},
                )
            except Exception:
                pass
            normalise_auth_response_timing(start_time)
            return Response(AUTH_FAILURE_RESPONSE, status=400)

        if user is None:
            try:
                log_action(
                    user=None,
                    action="login_failed",
                    resource_type="User",
                    ip_address=ip,
                    user_agent=ua,
                    device_fingerprint=_device_fingerprint(ip, ua),
                    request_method=request.method,
                    endpoint_path=request.path,
                    metadata={"reason": "invalid_credentials"},
                )
            except Exception:
                pass
            normalise_auth_response_timing(start_time)
            return Response(AUTH_FAILURE_RESPONSE, status=400)

        request.session.cycle_key()

        # If user has MFA enrolled, park credentials in the session and ask
        # the frontend to collect the TOTP code before granting a session (SFR-02b).
        has_mfa = TOTPDevice.objects.filter(user=user, confirmed=True).exists()
        if has_mfa:
            request.session["_mfa_pending_user_id"] = str(user.pk)
            request.session["_mfa_pending_backend"] = user.backend
            try:
                log_action(
                    user=user,
                    action="login_mfa_pending",
                    resource_type="User",
                    resource_id=user.id,
                    ip_address=ip,
                    user_agent=ua,
                    device_fingerprint=_device_fingerprint(ip, ua),
                    role="staff" if user.is_staff else "user",
                    request_method=request.method,
                    endpoint_path=request.path,
                    metadata={"reason": "mfa_required"},
                )
            except Exception:
                pass
            normalise_auth_response_timing(start_time)
            return Response({"mfa_required": True}, status=200)

        django_login(request, user)

        # Log successful login with session creation (NFSR-AC-02).
        try:
            log_action(
                user=user,
                action="login_success",
                resource_type="User",
                resource_id=user.id,
                ip_address=ip,
                user_agent=ua,
                device_fingerprint=_device_fingerprint(ip, ua),
                role="staff" if user.is_staff else "user",
                request_method=request.method,
                endpoint_path=request.path,
                metadata={"session_key": request.session.session_key},
            )
        except Exception:
            pass

        # Notify user if this is a new device/location.
        notify_new_device_or_location(request, user)

        normalise_auth_response_timing(start_time)
        return Response(UserProfileSerializer(user).data, status=200)


class LogoutView(APIView):
    """End the current session."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        try:
            log_action(
                user=user,
                action="logout",
                resource_type="User",
                resource_id=user.id,
                ip_address=ip,
                user_agent=ua,
                device_fingerprint=_device_fingerprint(ip, ua),
                role="staff" if user.is_staff else "user",
                request_method=request.method,
                endpoint_path=request.path,
            )
        except Exception:
            pass
        django_logout(request)
        return Response({"detail": "Signed out."}, status=200)
