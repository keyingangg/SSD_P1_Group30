"""API views for the accounts app."""
import base64
import io
import logging
import smtplib
import time

import qrcode
from auditlog.models import LogEntry
from axes.utils import reset
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.signals import user_login_failed
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied
from django.core.mail import BadHeaderError
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminUser, IsEmailVerified

logger = logging.getLogger("securebid")

from .emails import (
    send_invite_email,
    send_new_login_email,
    send_password_reset_email,
    send_verification_email,
)

from .models import (
    AccountLockoutProfile,
    EmailVerificationToken,
    PasswordResetToken,
    StaffInviteToken,
    UserSessionRecord,
)

from .serializers import (
    AcceptInviteSerializer,
    AdminUserListSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    StaffInviteSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)
from .tokens import (
    generate_email_verification_token,
    generate_password_reset_token,
    generate_staff_invite_token,
    validate_token,
)

User = get_user_model()


def _log_mfa_event(user, action_name, request):
    """Write an audit log entry for MFA enrolment/disablement (NFSR-AC-02)."""
    LogEntry.objects.create(
        content_type=ContentType.objects.get_for_model(user),
        object_pk=str(user.pk),
        object_repr=str(user),
        action=LogEntry.Action.UPDATE,
        changes={action_name: [None, True]},
        actor=user,
        remote_addr=get_client_ip(request),
    )


# Uniform response used for every registration outcome to prevent account
# enumeration (SFR-01d / AR-01).
REGISTRATION_RESPONSE = {
    "detail": "If that email can be registered, a verification link has been "
    "sent. Please check your inbox."
}

# Uniform response used for every failed login outcome to prevent account
# enumeration (NFSR-AU-05).
AUTH_FAILURE_RESPONSE = {
    "detail": "Invalid credentials or account not found."
}

# Minimum response time for login attempts to reduce timing-based enumeration.
AUTH_MIN_RESPONSE_SECONDS = 0.5


def normalise_auth_response_timing(start_time):
    """Ensure login responses take at least a fixed minimum time."""
    elapsed = time.perf_counter() - start_time
    remaining = AUTH_MIN_RESPONSE_SECONDS - elapsed

    if remaining > 0:
        time.sleep(remaining)


def invalidate_all_user_sessions(user):
    """Delete all active sessions belonging to this user."""
    active_sessions = Session.objects.filter(expire_date__gte=timezone.now())

    for session in active_sessions:
        data = session.get_decoded()

        if str(user.id) == str(data.get("_auth_user_id")):
            session.delete()


def get_client_ip(request):
    """Get client IP address from the request."""
    return request.META.get("REMOTE_ADDR")


def notify_new_device_or_location(request, user):
    """Notify user when a new IP address and browser combination logs in."""
    ip_address = get_client_ip(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    record, created = UserSessionRecord.objects.get_or_create(
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if created:
        try:
            send_new_login_email(
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception as exc:
            logger.error("Failed to send new login email to %s: %s", user.email, exc)


def clear_expired_lockout(email):
    """Clear django-axes and custom lockout if the custom lockout has expired."""
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return

    profile = getattr(user, "lockout_profile", None)

    if profile and profile.locked_until and profile.locked_until <= timezone.now():
        profile.locked_until = None
        profile.save(update_fields=["locked_until"])

        # Clear django-axes attempts so the user can login after lockout expiry.
        reset(username=user.email)


class CSRFView(APIView):
    """Set the CSRF cookie so the SPA can make authenticated unsafe requests."""

    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"detail": "CSRF cookie set."})


class RegisterView(APIView):
    """Register a new (inactive) account and send a verification email."""

    permission_classes = [AllowAny]

    def post(self, request):
        start_time = time.perf_counter()

        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

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
            elif not existing.is_email_verified:
                # Account exists but never verified: resend the link.
                raw_token = generate_email_verification_token(existing)
                send_verification_email(existing, raw_token)
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

        record.is_used = True
        record.save(update_fields=["is_used"])

        return Response(
            {"detail": "Your email has been verified. You can now sign in."},
            status=200,
        )


class LoginView(APIView):
    """Authenticate a verified user and start a session."""

    permission_classes = [AllowAny]

    def post(self, request):
        start_time = time.perf_counter()

        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        # django-axes wraps authenticate(); a locked account raises
        # PermissionDenied. Unverified accounts are inactive, so authenticate()
        # returns None for them -> the same generic error (no enumeration).
        try:
            clear_expired_lockout(email)
            user = authenticate(request, username=email, email=email, password=password)
        except PermissionDenied:
            normalise_auth_response_timing(start_time)
            return Response(AUTH_FAILURE_RESPONSE, status=400)

        if user is None:
            normalise_auth_response_timing(start_time)
            return Response(AUTH_FAILURE_RESPONSE, status=400)

        request.session.cycle_key()

        # If user has MFA enrolled, park credentials in the session and ask
        # the frontend to collect the TOTP code before granting a session (SFR-02b).
        has_mfa = TOTPDevice.objects.filter(user=user, confirmed=True).exists()
        if has_mfa:
            request.session["_mfa_pending_user_id"] = str(user.pk)
            request.session["_mfa_pending_backend"] = user.backend
            normalise_auth_response_timing(start_time)
            return Response({"mfa_required": True}, status=200)

        django_login(request, user)

        # Notify user if this is a new device/location.
        notify_new_device_or_location(request, user)

        normalise_auth_response_timing(start_time)
        return Response(UserProfileSerializer(user).data, status=200)


class LogoutView(APIView):
    """End the current session."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        django_logout(request)
        return Response({"detail": "Signed out."}, status=200)


class UserProfileView(APIView):
    """Read (and later update) the authenticated user's own profile."""

    permission_classes = [IsEmailVerified]

    def get(self, request):
        return Response(UserProfileSerializer(request.user).data, status=200)

    def patch(self, request):
        # TODO: allow updating safe profile fields (e.g. display_name).
        return Response({"detail": "Not implemented."}, status=501)


class PasswordResetRequestView(APIView):
    """Request a password reset link."""

    permission_classes = [AllowAny]

    def post(self, request):
        start_time = time.perf_counter()

        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(
                email=email, is_active=True, is_email_verified=True
            )
            raw_token = generate_password_reset_token(user)
            send_password_reset_email(user, raw_token)
        except User.DoesNotExist:
            pass  # Respond identically — no account enumeration.
        except (BadHeaderError, OSError) as exc:
            logger.error("Failed to send password reset email to %s: %s", email, exc)

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
        if record is None:
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

        record.is_used = True
        record.save(update_fields=["is_used"])

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

        return Response(
            {"detail": "Password updated. You can now sign in."},
            status=200,
        )


class PasswordChangeView(APIView):
    """Allow an authenticated user to change their password."""

    permission_classes = [IsEmailVerified]

    def post(self, request):
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not current_password or not new_password:
            return Response(
                {"detail": "Current password and new password are required."},
                status=400,
            )

        if not request.user.check_password(current_password):
            return Response(
                {"detail": "Current password is incorrect."},
                status=400,
            )

        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])

        # Invalidate all active sessions across all devices.
        invalidate_all_user_sessions(request.user)

        return Response(
            {"detail": "Password changed successfully. Please sign in again."},
            status=200,
        )


class StaffInviteView(APIView):
    """Send a staff invitation to a new admin team member (admin only).

    Creates an inactive staff account with an unusable password so the
    inviting admin never handles a credential. The invitee sets their own
    password when they accept the link.
    """

    permission_classes = [IsAdminUser]
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
        try:
            user = User.objects.create_user(
                email=email,
                display_name=email.split("@")[0][:100],
                password=None,
                is_active=False,
                is_staff=True,
                is_email_verified=False,
            )
            raw_token = generate_staff_invite_token(user, invited_by=request.user)
            send_invite_email(user, raw_token, invited_by=request.user)

            LogEntry.objects.log_create(
                instance=user,
                action=LogEntry.Action.CREATE,
                changes={
                    "event": "STAFF_INVITE",
                    "invited_by": request.user.email,
                    "invited_by_id": str(request.user.id),
                    "staff_user_email": user.email,
                    "staff_user_id": str(user.id),
                },
                actor=request.user,
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

        record = validate_token(token_string, StaffInviteToken)
        if record is None:
            return Response(
                {
                    "detail": "This invitation link is invalid or has expired. "
                    "Please ask an admin to resend it."
                },
                status=400,
            )

        user = record.user
        user.display_name = display_name
        user.set_password(password)
        user.is_active = True
        user.is_email_verified = True
        user.save(
            update_fields=[
                "display_name",
                "password",
                "is_active",
                "is_email_verified",
            ]
        )

        record.is_used = True
        record.save(update_fields=["is_used"])

        return Response(
            {"detail": "Account set up successfully. You can now sign in."},
            status=200,
        )


class DeleteAccountView(APIView):
    """Permanently delete the authenticated user's account (SFR-05a).

    If MFA is enrolled, a valid TOTP code must be supplied in the request body.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
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

        email = user.email
        invalidate_all_user_sessions(user)
        user.delete()
        logger.info("User %s deleted their own account", email)
        return Response({"detail": "Your account has been deleted."}, status=200)


class AdminUserListView(APIView):
    """Return all user accounts for the admin panel (staff only)."""

    permission_classes = [IsAdminUser]
    staff_only = True

    def get(self, request):
        qs = User.objects.all().order_by("-created_at")
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

    def _get_target(self, request, user_id):
        """Return (user, error_response) — one of the two will be None."""
        if not request.user.is_staff:
            return None, Response({"detail": "Admin access required."}, status=403)
        try:
            target = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None, Response({"detail": "User not found."}, status=404)
        if target.pk == request.user.pk:
            return None, Response(
                {"detail": "You cannot perform this action on your own account."},
                status=400,
            )
        if target.is_superuser:
            return None, Response(
                {"detail": "Superuser accounts cannot be modified here."},
                status=403,
            )
        return target, None

    def patch(self, request, user_id):
        """Toggle is_active (lock / unlock)."""
        target, err = self._get_target(request, user_id)
        if err:
            return err

        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])
        action = "unlocked" if target.is_active else "locked"
        logger.info("Admin %s %s account %s", request.user.email, action, target.email)
        return Response({"detail": f"Account {action}.", "is_active": target.is_active})

    def delete(self, request, user_id):
        """Permanently delete a user account."""
        target, err = self._get_target(request, user_id)
        if err:
            return err

        email = target.email
        target.delete()
        logger.info("Admin %s deleted account %s", request.user.email, email)
        return Response({"detail": "Account deleted."}, status=200)


# ---------------------------------------------------------------------------
# MFA (TOTP) views — SFR-02b / NFSR-AU-01 / NFSR-AU-04 / NFSR-AC-02
# ---------------------------------------------------------------------------

class MFAStatusView(APIView):
    """Return whether the authenticated user has MFA enrolled."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        enrolled = TOTPDevice.objects.filter(
            user=request.user, confirmed=True
        ).exists()
        return Response({"enrolled": enrolled})


class MFAEnrolView(APIView):
    """Begin MFA enrolment: generate a TOTP secret and return a QR code.

    The secret is generated by django-otp using os.urandom (CSPRNG) and stored
    in otp_totp_totpdevice, protected at rest by Supabase AES-256 (NFSR-AU-01).
    The device is left unconfirmed until the user verifies their first code.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Drop any previous unconfirmed device so enrolment is idempotent.
        TOTPDevice.objects.filter(user=request.user, confirmed=False).delete()

        device = TOTPDevice.objects.create(
            user=request.user,
            name=request.user.email,
            confirmed=False,
        )

        qr = qrcode.QRCode()
        qr.add_data(device.config_url)
        qr.make(fit=True)
        img = qr.make_image()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode()

        return Response({"qr_code": qr_b64})


class MFAEnrolConfirmView(APIView):
    """Complete MFA enrolment by verifying the user's first TOTP code."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        otp_code = request.data.get("otp_code", "").replace(" ", "")

        device = TOTPDevice.objects.filter(
            user=request.user, confirmed=False
        ).first()

        if device is None:
            return Response(
                {"detail": "No pending MFA setup found. Please start again."},
                status=400,
            )

        if not device.verify_token(otp_code):
            user_login_failed.send(
                sender=request.user.__class__,
                credentials={"username": request.user.email},
                request=request,
            )
            return Response({"detail": "Invalid code. Please try again."}, status=400)

        device.confirmed = True
        device.save(update_fields=["confirmed"])

        _log_mfa_event(request.user, "mfa_enrolled", request)
        logger.info("MFA enrolled for user %s", request.user.email)

        return Response({"detail": "MFA enabled successfully."}, status=200)


class MFAUnenrolView(APIView):
    """Disable MFA by removing the user's TOTP device."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        deleted, _ = TOTPDevice.objects.filter(user=request.user).delete()

        if not deleted:
            return Response(
                {"detail": "MFA is not enabled on this account."}, status=400
            )

        _log_mfa_event(request.user, "mfa_disabled", request)
        logger.info("MFA disabled for user %s", request.user.email)

        return Response({"detail": "MFA disabled successfully."}, status=200)


class MFALoginVerifyView(APIView):
    """Complete a pending MFA login by verifying the TOTP code.

    The user's identity was already confirmed by password in LoginView.
    Only the session token grants access — the session is not fully
    authenticated until this step succeeds.

    Invalid codes are counted toward the django-axes lockout threshold
    (NFSR-AU-04). The TOTPDevice.last_t column prevents token replay within
    the same 30-second window (SFR-02b).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.session.get("_mfa_pending_user_id")
        backend = request.session.get("_mfa_pending_backend")

        if not user_id:
            return Response(
                {"detail": "No pending MFA verification. Please log in again."},
                status=400,
            )

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "Session expired. Please log in again."}, status=400
            )

        otp_code = request.data.get("otp_code", "").replace(" ", "")
        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()

        if device is None or not device.verify_token(otp_code):
            user_login_failed.send(
                sender=user.__class__,
                credentials={"username": user.email},
                request=request,
            )
            return Response({"detail": "Invalid code. Please try again."}, status=400)

        # Clear pending markers before elevating to a full session.
        del request.session["_mfa_pending_user_id"]
        del request.session["_mfa_pending_backend"]

        user.backend = backend
        django_login(request, user)
        notify_new_device_or_location(request, user)

        return Response(UserProfileSerializer(user).data, status=200)