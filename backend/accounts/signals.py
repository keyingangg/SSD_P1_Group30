import logging

from auditlog.models import LogEntry
from core.audit import log_action
from axes.signals import user_locked_out
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.utils import timezone

from .emails import send_account_lockout_email
from .lockout import apply_escalating_lockout
from .models import AccountLockoutProfile

logger = logging.getLogger("securebid")


def get_client_ip(request):
    """Get client IP address from the request."""
    if request is None:
        return None

    return request.META.get("REMOTE_ADDR")


@receiver(user_locked_out)
def handle_user_locked_out(sender, request, username=None, ip_address=None, **kwargs):
    """
    Runs whenever django-axes locks a login identity.
    """
    User = get_user_model()

    email = username

    if not email and request is not None:
        email = request.data.get("email") if hasattr(request, "data") else None

    if not email and request is not None:
        email = request.POST.get("email")

    if not email:
        return

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return

    ip = ip_address or get_client_ip(request)

    profile, _created = AccountLockoutProfile.objects.get_or_create(user=user)

    # Idempotency guard: only escalate when there is no currently active
    # custom lockout. Without this, a signal that re-fires for a retry made
    # while the account is already locked (e.g. axes re-evaluating the same
    # blocked attempt) would bump lockout_level and send a duplicate email
    # every time, escalating far faster than the intended 5-failure cadence.
    if profile.locked_until and profile.locked_until > timezone.now():
        logger.info(
            "Ignoring duplicate lockout signal for %s; lockout already active until %s",
            user.email,
            profile.locked_until,
        )
        return

    duration = apply_escalating_lockout(profile, ip)

    try:
        send_account_lockout_email(
            user=user,
            ip_address=ip,
            locked_until=profile.locked_until,
            lockout_duration=duration,
        )
    except Exception as exc:
        logger.error("Failed to send account lockout email to %s: %s", user.email, exc)
    LogEntry.objects.log_create(
        instance=user,
        action=LogEntry.Action.UPDATE,
        changes={
            "event": "ACCOUNT_LOCKOUT",
            "user_id": str(user.id),
            "ip_address": ip,
            "timestamp": timezone.now().isoformat(),
            "locked_until": profile.locked_until.isoformat()
            if profile.locked_until
            else None,
            "lockout_duration": str(duration),
            "lockout_level": profile.lockout_level,
        },
    )

    # Also write our structured audit trail entry (append-only, masked)
    try:
        log_action(
            user=user,
            action="ACCOUNT_LOCKOUT",
            resource_type="user",
            resource_id=user.id,
            ip_address=ip,
            user_agent=getattr(request, "META", {}).get("HTTP_USER_AGENT", "") if request else "",
            role=getattr(user, "role", "") or (getattr(user, "is_staff", False) and "staff" or "user"),
            metadata={
                "locked_until": profile.locked_until.isoformat() if profile.locked_until else None,
                "lockout_duration": str(duration),
                "lockout_level": profile.lockout_level,
            },
        )
    except Exception:
        logger.exception("Failed to write structured audit log for lockout of %s", user.email)