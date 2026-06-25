"""Serializers for the accounts app."""
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .password import is_password_breached

User = get_user_model()


class UserRegistrationSerializer(serializers.Serializer):
    """Validate registration input (email + password).

    Password policy (NFSR-AU-01): 12–128 characters and not present in a known
    breach corpus. No composition rules are imposed.
    """

    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True, min_length=12, max_length=128, trim_whitespace=False
    )

    def validate_email(self, value):
        return value.strip().lower()

    def validate_password(self, value):
        if is_password_breached(value):
            raise serializers.ValidationError(
                "This password has appeared in a known data breach. "
                "Please choose a different one."
            )
        return value


class UserLoginSerializer(serializers.Serializer):
    """Validate login credentials."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        return value.strip().lower()


class UserProfileSerializer(serializers.ModelSerializer):
    """Serialize the authenticated user's own profile (safe fields only)."""

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "display_name",
            "is_email_verified",
            "is_staff",
            "created_at",
        ]
        read_only_fields = fields


class PasswordResetRequestSerializer(serializers.Serializer):
    """Validate a password reset request (email)."""

    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Validate a password reset confirmation (token + new password)."""

    token = serializers.CharField(max_length=512)
    password = serializers.CharField(
        write_only=True, min_length=12, max_length=128, trim_whitespace=False
    )

    def validate_password(self, value):
        if is_password_breached(value):
            raise serializers.ValidationError(
                "This password has appeared in a known data breach. "
                "Please choose a different one."
            )
        return value


class StaffInviteSerializer(serializers.Serializer):
    """Validate a staff invitation request (email only)."""

    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class AdminUserListSerializer(serializers.ModelSerializer):
    """Read-only serializer for the admin user list view."""

    role = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "display_name", "role", "status", "created_at"]
        read_only_fields = fields

    def get_role(self, obj):
        if obj.is_superuser:
            return "Superuser"
        if obj.is_staff:
            return "Staff"
        return "Bidder"

    def get_status(self, obj):
        if obj.is_active:
            return "Active"
        if not obj.is_email_verified:
            return "Pending"
        return "Locked"


class AcceptInviteSerializer(serializers.Serializer):
    """Validate an invite acceptance (token + display name + password)."""

    # Max token length prevents oversized payloads from reaching the DB lookup
    # (NFSR-IN-03).
    token = serializers.CharField(max_length=512)
    display_name = serializers.CharField(min_length=1, max_length=100)
    password = serializers.CharField(
        write_only=True, min_length=12, max_length=128, trim_whitespace=False
    )

    def validate_display_name(self, value):
        return value.strip()

    def validate_password(self, value):
        if is_password_breached(value):
            raise serializers.ValidationError(
                "This password has appeared in a known data breach. "
                "Please choose a different one."
            )
        return value
