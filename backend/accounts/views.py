"""API views for the accounts app.

Implements registration with email verification and session-based login.
MFA/OTP is intentionally out of scope here and will be added separately.
"""
import logging
import smtplib

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.core.exceptions import PermissionDenied
from django.core.mail import BadHeaderError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("securebid")

from .emails import send_invite_email, send_password_reset_email, send_verification_email
from .models import EmailVerificationToken, PasswordResetToken, StaffInviteToken
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

# Uniform response used for every registration outcome to prevent account
# enumeration (SFR-01d / AR-01).
REGISTRATION_RESPONSE = {
    "detail": "If that email can be registered, a verification link has been "
    "sent. Please check your inbox."
}


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
            return Response(
                {"detail": "We could not send the verification email. "
                 "Please check your email address and try again shortly."},
                status=503,
            )

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
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        # django-axes wraps authenticate(); a locked account raises
        # PermissionDenied. Unverified accounts are inactive, so authenticate()
        # returns None for them -> the same generic error (no enumeration).
        try:
            user = authenticate(request, username=email, password=password)
        except PermissionDenied:
            return Response(
                {
                    "detail": "Too many failed attempts. Your account is "
                    "temporarily locked. Try again later."
                },
                status=403,
            )

        if user is None:
            return Response(
                {"detail": "Invalid credentials or account not found."},
                status=400,
            )

        django_login(request, user)
        return Response(UserProfileSerializer(user).data, status=200)


class LogoutView(APIView):
    """End the current session."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        django_logout(request)
        return Response({"detail": "Signed out."}, status=200)


class UserProfileView(APIView):
    """Read (and later update) the authenticated user's own profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserProfileSerializer(request.user).data, status=200)

    def patch(self, request):
        # TODO: allow updating safe profile fields (e.g. display_name).
        return Response({"detail": "Not implemented."}, status=501)


class PasswordResetRequestView(APIView):
    """Request a password reset link."""

    permission_classes = [AllowAny]

    def post(self, request):
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

        return Response(
            {"detail": "Password updated. You can now sign in."},
            status=200,
        )


class StaffInviteView(APIView):
    """Send a staff invitation to a new admin team member (admin only).

    Creates an inactive staff account with an unusable password so the
    inviting admin never handles a credential. The invitee sets their own
    password when they accept the link.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_staff:
            return Response({"detail": "Admin access required."}, status=403)

        serializer = StaffInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        if User.objects.filter(email=email).exists():
            return Response(
                {"detail": "An account with that email already exists."},
                status=400,
            )

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
        except (BadHeaderError, smtplib.SMTPException, OSError) as exc:
            logger.error("Failed to send staff invite to %s: %s", email, exc)
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
        user.save(update_fields=["display_name", "password", "is_active", "is_email_verified"])

        record.is_used = True
        record.save(update_fields=["is_used"])

        return Response(
            {"detail": "Account set up successfully. You can now sign in."},
            status=200,
        )


class DeleteAccountView(APIView):
    """Request permanent deletion / anonymisation of the account."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # TODO: re-confirm identity, block if unpaid wins, anonymise PII.
        return Response({"detail": "Not implemented."}, status=501)


class AdminUserListView(APIView):
    """Return all user accounts for the admin panel (staff only)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response({"detail": "Admin access required."}, status=403)

        qs = User.objects.all().order_by("-created_at")
        serializer = AdminUserListSerializer(qs, many=True)
        return Response(serializer.data)


class AdminUserDetailView(APIView):
    """Lock/unlock or delete a single user account (staff only).

    Guards:
    - Cannot act on your own account.
    - Cannot act on a superuser account (superusers are managed via Django shell).
    """

    permission_classes = [IsAuthenticated]

    def _get_target(self, request, user_id):
        """Return (user, error_response) — one of the two will be None."""
        if not request.user.is_staff:
            return None, Response({"detail": "Admin access required."}, status=403)
        try:
            target = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None, Response({"detail": "User not found."}, status=404)
        if target.pk == request.user.pk:
            return None, Response({"detail": "You cannot perform this action on your own account."}, status=400)
        if target.is_superuser:
            return None, Response({"detail": "Superuser accounts cannot be modified here."}, status=403)
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
