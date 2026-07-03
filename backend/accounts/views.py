"""API views for the accounts app."""
import base64
import io
import logging
import smtplib
import time

from django.db.models import Q

import qrcode
from axes.utils import reset
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.signals import user_login_failed
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied
from django.core.mail import BadHeaderError
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django_ratelimit.decorators import ratelimit
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminUser, IsEmailVerified, IsSuperUser
from core.audit import log_action, device_fingerprint as _device_fingerprint

logger = logging.getLogger("securebid")

from .emails import (
    send_invite_email,
    send_new_login_email,
    send_password_reset_email,
    send_verification_email,
)
from .anonymisation import anonymise_user_data
from .password import is_password_breached

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
    """Write a structured audit log entry for MFA enrolment/disablement (NFSR-AC-02)."""
    ip = get_client_ip(request)
    ua = request.META.get("HTTP_USER_AGENT", "") if request else ""
    log_action(
        user=user,
        action=action_name,
        resource_type="User",
        resource_id=user.id,
        ip_address=ip,
        user_agent=ua,
        device_fingerprint=_device_fingerprint(ip, ua),
        role="staff" if getattr(user, "is_staff", False) else "user",
        request_method=getattr(request, "method", ""),
        endpoint_path=getattr(request, "path", ""),
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


class UserProfileView(APIView):
    """Read the authenticated user's own profile."""

    permission_classes = [IsEmailVerified]

    def get(self, request):
        return Response(UserProfileSerializer(request.user).data, status=200)


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
        from payments.models import Order

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


class AdminUserListView(APIView):
    """Return all user accounts for the admin panel (staff only)."""

    permission_classes = [IsAdminUser]
    staff_only = True

    def get(self, request):
        qs = User.objects.filter(is_anonymised=False).order_by("-created_at")
        serializer = AdminUserListSerializer(qs, many=True)
        return Response(serializer.data)


def _get_admin_target(request, user_id):
    """Return (user, error_response) — one of the two will be None.

    Guards shared by every admin action that operates on another user's
    account: cannot act on your own account, a superuser account, or an
    already-anonymised account.
    """
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
    if target.is_anonymised:
        return None, Response({"detail": "User not found."}, status=404)
    return target, None


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
        target, err = _get_admin_target(request, user_id)
        if err:
            return err

        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])
        action = "unlocked" if target.is_active else "locked"
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
        return Response({"detail": f"Account {action}.", "is_active": target.is_active})

    def delete(self, request, user_id):
        """Permanently delete a user account."""
        target, err = _get_admin_target(request, user_id)
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
        invalidate_all_user_sessions(target)
        anonymise_user_data(target)
        logger.info("Admin %s deleted and anonymised account %s", request.user.email, email)
        return Response({"detail": "Account deleted."}, status=200)


class AdminTerminateSessionsView(APIView):
    """Kill a user's live session(s) without locking or deleting the account (FSR-C-07)."""

    permission_classes = [IsAdminUser]
    staff_only = True
    http_method_names = ["post"]

    def post(self, request, user_id):
        target, err = _get_admin_target(request, user_id)
        if err:
            return err

        invalidate_all_user_sessions(target)
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


class AdminDemoteStaffView(APIView):
    """Demote an existing staff member back to a regular user (staff only).

    The counterpart to StaffInviteView (promotion). Removes the is_staff
    privilege from an existing account, immediately terminates the target's live
    sessions so the privilege drop takes effect at once, and records the change
    in django-auditlog (admin_role_demoted, NFSR-AC-02). Guards mirror every
    other admin action via _get_admin_target: an admin cannot demote their own
    account, a superuser, or an anonymised account.

    Restricted to superusers: revoking staff privileges is a top-tier operation
    reserved for the owner account (least privilege).
    """

    permission_classes = [IsSuperUser]
    staff_only = True
    http_method_names = ["post"]

    def post(self, request, user_id):
        target, err = _get_admin_target(request, user_id)
        if err:
            return err

        # Only an actual staff member can be demoted — a regular bidder has no
        # elevated role to remove.
        if not target.is_staff:
            return Response(
                {"detail": "This account is not a staff member."},
                status=400,
            )

        target.is_staff = False
        target.save(update_fields=["is_staff"])

        # Drop the elevated privilege immediately by killing any live session,
        # forcing the (now regular) user to re-authenticate.
        invalidate_all_user_sessions(target)

        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        log_action(
            user=request.user,
            action="admin_role_demoted",
            resource_type="User",
            resource_id=target.id,
            ip_address=ip,
            user_agent=ua,
            device_fingerprint=_device_fingerprint(ip, ua),
            role="staff" if request.user.is_staff else "user",
            request_method=request.method,
            endpoint_path=request.path,
            metadata={
                "target_email": target.email,
                "old_role": "staff",
                "new_role": "user",
            },
        )
        logger.info(
            "Admin %s demoted staff account %s to regular user",
            request.user.email,
            target.email,
        )
        return Response(
            {"detail": "Staff member demoted to regular user.", "role": "Bidder"},
            status=200,
        )


class AdminPromoteUserView(APIView):
    """Promote an existing regular user to staff (staff only).

    The re-promotion counterpart to AdminDemoteStaffView, for restoring staff
    access to an account that already exists (e.g. one that was accidentally
    demoted). Unlike StaffInviteView — which creates a brand-new invited account
    and can only target an unused email — this elevates an existing, already
    registered user. Audit-logged as admin_role_promoted (NFSR-AC-02). Guards
    mirror every other admin action via _get_admin_target: an admin cannot
    promote their own account, a superuser, or an anonymised account.

    Restricted to superusers: granting staff privileges is a top-tier operation
    reserved for the owner account (least privilege).
    """

    permission_classes = [IsSuperUser]
    staff_only = True
    http_method_names = ["post"]

    def post(self, request, user_id):
        target, err = _get_admin_target(request, user_id)
        if err:
            return err

        if target.is_staff:
            return Response(
                {"detail": "This account is already a staff member."},
                status=400,
            )

        target.is_staff = True
        target.save(update_fields=["is_staff"])

        # Force a fresh login so the newly elevated role is reflected in the
        # target's session and admin UI on their next sign-in.
        invalidate_all_user_sessions(target)

        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        log_action(
            user=request.user,
            action="admin_role_promoted",
            resource_type="User",
            resource_id=target.id,
            ip_address=ip,
            user_agent=ua,
            device_fingerprint=_device_fingerprint(ip, ua),
            role="staff" if request.user.is_staff else "user",
            request_method=request.method,
            endpoint_path=request.path,
            metadata={
                "target_email": target.email,
                "old_role": "user",
                "new_role": "staff",
                "method": "direct",
            },
        )
        logger.info(
            "Admin %s promoted user %s to staff", request.user.email, target.email
        )
        return Response(
            {"detail": "User promoted to staff member.", "role": "Staff"},
            status=200,
        )


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

        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        otp_code = request.data.get("otp_code", "").replace(" ", "")
        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()

        if device is None or not device.verify_token(otp_code):
            user_login_failed.send(
                sender=user.__class__,
                credentials={"username": user.email},
                request=request,
            )
            try:
                log_action(
                    user=user,
                    action="mfa_login_failed",
                    resource_type="User",
                    resource_id=user.id,
                    ip_address=ip,
                    user_agent=ua,
                    device_fingerprint=_device_fingerprint(ip, ua),
                    role="staff" if user.is_staff else "user",
                    request_method=request.method,
                    endpoint_path=request.path,
                    metadata={"reason": "invalid_otp"},
                )
            except Exception:
                pass
            return Response({"detail": "Invalid code. Please try again."}, status=400)

        # Clear pending markers before elevating to a full session.
        del request.session["_mfa_pending_user_id"]
        del request.session["_mfa_pending_backend"]

        user.backend = backend
        django_login(request, user)
        notify_new_device_or_location(request, user)

        try:
            log_action(
                user=user,
                action="mfa_login_success",
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

        return Response(UserProfileSerializer(user).data, status=200)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

_ACTION_LABEL_MAP = {
    "login_success": "Login successful",
    "login_failed": "Login failed",
    "logout": "Logged out",
    "mfa_login_success": "MFA login successful",
    "mfa_login_failed": "MFA login failed",
    "mfa_enrolled": "MFA enrolled",
    "mfa_disabled": "MFA disabled",
    "bid_placed": "Bid placed",
    "bid_rejected": "Bid rejected",
    "admin_account_toggled": "Account locked/unlocked",
    "admin_account_deleted": "Account deleted",
    "admin_listing_status_changed": "Listing status changed",
    "admin_listing_deleted": "Listing deleted",
    "ORDER_PAID": "Payment received",
    "ORDER_FULFILLMENT_UPDATED": "Fulfillment updated",
    "ORDER_ACCESS_DENIED": "Order access denied",
    "CHECKOUT_ACCESS_DENIED": "Checkout access denied",
    "CHECKOUT_INITIATED": "Checkout initiated",
    "PAYMENT_WINNER_MISMATCH": "Payment winner mismatch",
    "PAYMENT_CONFIRM_MISMATCH": "Payment confirm mismatch",
}

_CATEGORY_FILTERS = {
    "login_logout": lambda qs: qs.filter(
        action__in=["login_success", "login_failed", "logout",
                    "mfa_login_success", "mfa_login_failed",
                    "mfa_enrolled", "mfa_disabled"]
    ),
    "bids": lambda qs: qs.filter(action__icontains="bid"),
    "admin_actions": lambda qs: qs.filter(action__istartswith="admin_"),
    "payments": lambda qs: qs.filter(
        action__in=["ORDER_PAID", "ORDER_FULFILLMENT_UPDATED",
                    "ORDER_ACCESS_DENIED", "CHECKOUT_ACCESS_DENIED",
                    "CHECKOUT_INITIATED", "PAYMENT_WINNER_MISMATCH",
                    "PAYMENT_CONFIRM_MISMATCH"]
    ) | qs.filter(resource_type="Order"),
    "errors": lambda qs: qs.exclude(exception_type=""),
}

# Categories a regular admin (non-superuser) may request.
_REGULAR_ADMIN_CATEGORIES = {"all", "bids"}

# For the "all" tab, regular admins only see auction + bid events.
def _restrict_to_auction_and_bids(qs):
    return qs.filter(
        Q(action__icontains="bid") | Q(action__icontains="listing")
    )


def _severity(entry):
    action = entry.action.lower()
    if entry.exception_type or "denied" in action or "error" in action:
        return "error"
    if "failed" in action or "rejected" in action or "mismatch" in action:
        return "warning"
    if entry.role in ("staff", "superuser", "admin") or action.startswith("admin_"):
        return "admin"
    return "success"


def _serialize_entry(entry):
    user = entry.user
    if user is not None:
        try:
            user_display = user.email
            is_admin = user.is_staff or user.is_superuser
        except Exception:
            user_display = "—"
            is_admin = False
    else:
        user_display = "System"
        is_admin = False

    action_label = _ACTION_LABEL_MAP.get(entry.action, entry.action.replace("_", " ").title())
    device = entry.device_fingerprint[:12] if entry.device_fingerprint else "—"

    ref = ""
    if entry.resource_type:
        ref = entry.resource_type
        if entry.resource_id:
            ref += f" {str(entry.resource_id)[:8]}"

    return {
        "timestamp": entry.timestamp.isoformat(),
        "user_display": user_display,
        "is_admin": is_admin,
        "action_label": action_label,
        "ip_address": entry.ip_address or "—",
        "device": device,
        "ref": ref or "—",
        "severity": _severity(entry),
    }


class AdminAuditLogView(APIView):
    """Return audit log entries for the admin panel (staff only).

    Access tiers (NFSR-AC-04 / FSR-AC-06):
    - Superuser: full trail, all categories including payments.
    - Regular admin: auction and bid logs only; payment/login/error
      categories are blocked with 403.
    Every read is itself logged (NFSR-AC-04).
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        from core.models import AuditLog

        is_superuser = request.user.is_superuser
        category = request.query_params.get("category", "all")
        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")

        # Enforce category-level access for regular admins.
        if not is_superuser and category not in _REGULAR_ADMIN_CATEGORIES:
            log_action(
                user=request.user,
                action="audit_log_access_denied",
                resource_type="AuditLog",
                ip_address=ip,
                user_agent=ua,
                device_fingerprint=_device_fingerprint(ip, ua),
                role="staff",
                request_method=request.method,
                endpoint_path=request.path,
                metadata={"category": category, "reason": "insufficient_role"},
            )
            return Response(
                {"detail": "You do not have permission to view this category."},
                status=403,
            )

        qs = AuditLog.objects.select_related("user").order_by("-timestamp")

        # Regular admins: restrict "all" to auction + bid events.
        if not is_superuser and category == "all":
            qs = _restrict_to_auction_and_bids(qs)
        else:
            filter_fn = _CATEGORY_FILTERS.get(category)
            if filter_fn:
                qs = filter_fn(qs)

        results = [_serialize_entry(e) for e in qs[:500]]

        # Log this read access (NFSR-AC-04).
        try:
            log_action(
                user=request.user,
                action="audit_log_read",
                resource_type="AuditLog",
                ip_address=ip,
                user_agent=ua,
                device_fingerprint=_device_fingerprint(ip, ua),
                role="superuser" if is_superuser else "staff",
                request_method=request.method,
                endpoint_path=request.path,
                metadata={"category": category, "result_count": len(results)},
            )
        except Exception:
            pass

        return Response(results)
