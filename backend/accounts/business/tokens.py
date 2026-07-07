"""Token generation and validation helpers for the accounts app.

Raw tokens are returned to the caller (to embed in a link) but only a SHA-256
hash is ever persisted, so a database leak does not expose usable tokens.
"""
import hashlib
import secrets
from datetime import timedelta

from django.utils import timezone
from django.utils.crypto import constant_time_compare

from ..data.models import EmailVerificationToken, PasswordResetToken, StaffInviteToken

EMAIL_TOKEN_TTL = timedelta(hours=24)
RESET_TOKEN_TTL = timedelta(minutes=10)
INVITE_TOKEN_TTL = timedelta(hours=48)


def _hash_token(raw_token):
    """Return the SHA-256 hex digest of a raw token."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_email_verification_token(user):
    """Create a one-time email verification token (24h expiry).

    Returns the raw token to embed in the verification link.
    """
    raw_token = secrets.token_urlsafe(32)
    EmailVerificationToken.objects.create(
        user=user,
        token=_hash_token(raw_token),
        expires_at=timezone.now() + EMAIL_TOKEN_TTL,
    )
    return raw_token


def generate_password_reset_token(user):
    """Create a one-time, time-limited password reset token (10min expiry).

    Returns the raw token to embed in the reset link.
    """
    raw_token = secrets.token_urlsafe(32)
    PasswordResetToken.objects.create(
        user=user,
        token=_hash_token(raw_token),
        expires_at=timezone.now() + RESET_TOKEN_TTL,
    )
    return raw_token


def generate_staff_invite_token(user, invited_by):
    """Create a 48-hour staff invitation token.

    Returns the raw token to embed in the invite link.
    The invited user has an unusable password until they accept.
    """
    raw_token = secrets.token_urlsafe(32)
    StaffInviteToken.objects.create(
        user=user,
        invited_by=invited_by,
        token=_hash_token(raw_token),
        expires_at=timezone.now() + INVITE_TOKEN_TTL,
    )
    return raw_token


def validate_token(token_string, token_model):
    """Validate a raw token against a token model using constant-time comparison.

    Returns the matching record only if it exists, is unused, and unexpired;
    otherwise returns None.
    """
    if not token_string:
        return None

    candidate_hash = _hash_token(token_string)
    now = timezone.now()

    records = token_model.objects.filter(
        is_used=False,
        expires_at__gte=now,
    )

    for record in records:
        if constant_time_compare(record.token, candidate_hash):
            return record

    return None
