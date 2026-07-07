"""PII anonymisation service for PDPA compliance (NFSR-C-08 · SFR-05c).

Upon account deletion, all PII is anonymised in-place within 30 days,
preserving auction integrity and audit trail continuity.

PII anonymised on deletion:
- User.email            → deleted-{uuid}@anon.invalid
- User.display_name     → "Deleted User"
- User.password         → unusable (argon2 placeholder)
- Order.delivery_address_snapshot → "[REDACTED]"
- AuditLog.ip_address   → None
- AuditLog.user_agent   → ""
- AuditLog.device_fingerprint → ""

Records preserved (non-PII):
- Bid records (amount, anonymous_identifier, submitted_at, is_winning)
- Order records (stripe_payment_intent_id, fulfillment_status, winning_bid)
- AuditLog entries (action, timestamp, resource, before/after data)
- Listing records created by admin staff
"""
import logging

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("securebid")


def _anonymised_email(user_id: str) -> str:
    return f"deleted-{user_id}@anon.invalid"


def anonymise_user_data(user) -> None:
    """Anonymise all PII for a user whose account is being deleted.

    Safe to call multiple times — is_anonymised guard prevents double-runs.
    """
    if user.is_anonymised:
        return

    from core.models import AuditLog
    from payments.models import Order

    user_id = user.id

    with transaction.atomic():
        # Delete auth/session tokens — no longer needed after deletion.
        user.email_verification_tokens.all().delete()
        user.password_reset_tokens.all().delete()
        user.staff_invite_tokens.all().delete()
        user.session_records.all().delete()

        # Delete MFA device.
        try:
            from django_otp.plugins.otp_totp.models import TOTPDevice
            TOTPDevice.objects.filter(user=user).delete()
        except Exception:
            pass

        # Delete lockout profile.
        try:
            user.lockout_profile.delete()
        except Exception:
            pass

        # Anonymise User PII — email freed for potential re-registration.
        user.email = _anonymised_email(user_id)
        user.display_name = "Deleted User"
        user.is_active = False
        user.set_unusable_password()
        user.deleted_at = user.deleted_at or timezone.now()
        user.is_anonymised = True
        user.anonymised_at = timezone.now()
        user.save(update_fields=[
            "email", "display_name", "is_active", "password",
            "deleted_at", "is_anonymised", "anonymised_at",
        ])

        # Anonymise delivery addresses in orders owned by this user.
        Order.objects.filter(winner_id=user_id).update(
            delivery_address_snapshot="[REDACTED]"
        )

        # Scrub IP/UA from this user's own audit log entries.
        # QuerySet.update() bypasses AuditLog.save() so the append-only
        # guard does not fire. row_hash is overwritten to signal redaction.
        AuditLog.objects.filter(user_id=user_id).update(
            ip_address=None,
            user_agent="",
            device_fingerprint="",
            row_hash="[PII_ANONYMISED]",
        )

    logger.info("PII anonymised for deleted user %s", user_id)
