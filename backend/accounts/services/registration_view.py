"""Registration + email verification API (diagram: svc_register)."""
import logging
import time

from django.contrib.auth import get_user_model
from django.core.mail import BadHeaderError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.cross_cutting.audit import log_action, device_fingerprint as _device_fingerprint

from ..business.emails import send_verification_email
from ..business.session_manager import get_client_ip, normalise_auth_response_timing
from ..business.tokens import generate_email_verification_token, validate_token
from ..data.models import EmailVerificationToken
from .serializers import UserRegistrationSerializer

logger = logging.getLogger("securebid")

User = get_user_model()

# Uniform response used for every registration outcome to prevent account
# enumeration (SFR-01d / AR-01).
REGISTRATION_RESPONSE = {
    "detail": "If that email can be registered, a verification link has been "
    "sent. Please check your inbox."
}


class RegisterView(APIView):
    """Register a new (inactive) account and send a verification email."""

    permission_classes = [AllowAny]

    def post(self, request):
        start_time = time.perf_counter()

        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")

        existing = User.objects.filter(email=email).first()
        try:
            if existing is None:
                # display_name is required by the model; the Create Account form
                # does not collect one, so default to the email local-part.
                display_name = email.split("@")[0][:100]
                user = User.objects.create_user(
                    email=email,
                    display_name=display_name,
                    password=password,
                    is_active=False,
                    is_email_verified=False,
                )
                raw_token = generate_email_verification_token(user)
                send_verification_email(user, raw_token)
                log_action(
                    user=user,
                    action="user_registered",
                    resource_type="User",
                    resource_id=user.id,
                    ip_address=ip,
                    user_agent=ua,
                    device_fingerprint=_device_fingerprint(ip, ua),
                    role="user",
                    request_method=request.method,
                    endpoint_path=request.path,
                    metadata={"email": email},
                )
            elif not existing.is_email_verified:
                # Account exists but never verified: resend the link.
                raw_token = generate_email_verification_token(existing)
                send_verification_email(existing, raw_token)
                log_action(
                    user=existing,
                    action="user_registration_resend",
                    resource_type="User",
                    resource_id=existing.id,
                    ip_address=ip,
                    user_agent=ua,
                    device_fingerprint=_device_fingerprint(ip, ua),
                    role="user",
                    request_method=request.method,
                    endpoint_path=request.path,
                    metadata={"email": email},
                )
            # Verified account already exists: respond identically, do nothing.
        except (BadHeaderError, OSError) as exc:
            logger.error("Failed to send verification email to %s: %s", email, exc)
            normalise_auth_response_timing(start_time)
            return Response(
                {
                    "detail": "We could not send the verification email. "
                    "Please check your email address and try again shortly."
                },
                status=503,
            )

        normalise_auth_response_timing(start_time)
        return Response(REGISTRATION_RESPONSE, status=201)


class VerifyEmailView(APIView):
    """Verify an email address from a one-time token and activate the account."""

    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token") or request.query_params.get("token")
        record = validate_token(token, EmailVerificationToken)
        if record is None:
            return Response(
                {"detail": "This verification link is invalid or has expired."},
                status=400,
            )

        user = record.user
        user.is_email_verified = True
        user.is_active = True
        user.save(update_fields=["is_email_verified", "is_active"])

        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        log_action(
            user=user,
            action="email_verified",
            resource_type="User",
            resource_id=user.id,
            ip_address=ip,
            user_agent=ua,
            device_fingerprint=_device_fingerprint(ip, ua),
            role="user",
            request_method=request.method,
            endpoint_path=request.path,
            metadata={"email": user.email},
        )

        record.is_used = True
        record.save(update_fields=["is_used"])

        return Response(
            {"detail": "Your email has been verified. You can now sign in."},
            status=200,
        )
