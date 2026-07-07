"""User Schema — the custom identity model (diagram: data_user)."""
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
