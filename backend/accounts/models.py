"""Account, identity, and token models for SecureBid."""
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    """Manager for the custom email-based User model."""

    def create_user(self, email, display_name, password=None, **extra_fields):
        # TODO: enforce email/password policy at the serializer layer.
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, display_name=display_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, display_name, password=None, **extra_fields):
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_email_verified", True)
        return self.create_user(email, display_name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user identified by email, with a UUID primary key."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_anonymised = models.BooleanField(default=False)
    anonymised_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email


class EmailVerificationToken(models.Model):
    """One-time email verification link issued at registration."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="email_verification_tokens"
    )
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "email_verification_tokens"


class PasswordResetToken(models.Model):
    """One-time, time-limited password reset link."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="password_reset_tokens"
    )
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "password_reset_tokens"


class StaffInviteToken(models.Model):
    """One-time staff invitation token issued by an admin.

    The invited user has no usable password until they accept the invite and
    set one themselves — the inviting admin never handles a credential.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="staff_invite_tokens"
    )
    invited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="sent_invites"
    )
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "staff_invite_tokens"

class AccountLockoutProfile(models.Model):
    """Stores escalating account lockout state for a user."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="lockout_profile",
    )
    lockout_level = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_lockout_ip = models.GenericIPAddressField(null=True, blank=True)
    last_lockout_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "account_lockout_profiles"

    def is_locked(self):
        from django.utils import timezone

        return self.locked_until is not None and self.locked_until > timezone.now()

    def __str__(self):
        return f"Lockout profile for {self.user.email}"


class UserSessionRecord(models.Model):
    """Tracks known login devices/locations for new-session notifications."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="session_records",
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_session_records"
        unique_together = ("user", "ip_address", "user_agent")

    def __str__(self):
        return f"{self.user.email} - {self.ip_address}"