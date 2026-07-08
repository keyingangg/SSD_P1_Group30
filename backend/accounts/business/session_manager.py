"""Session Manager — login-session lifecycle helpers (diagram: biz_session)."""
import logging
import time
from importlib import import_module

from django.conf import settings
from django.contrib.sessions.models import Session
from django.utils import timezone

from .emails import send_new_login_email
from ..data.models import UserSessionRecord

logger = logging.getLogger("securebid")

# Minimum response time for login attempts to reduce timing-based enumeration.
AUTH_MIN_RESPONSE_SECONDS = 0.5


def normalise_auth_response_timing(start_time):
    """Ensure login responses take at least a fixed minimum time."""
    elapsed = time.perf_counter() - start_time
    remaining = AUTH_MIN_RESPONSE_SECONDS - elapsed

    if remaining > 0:
        time.sleep(remaining)


def get_client_ip(request):
    """Get client IP address from the request."""
    return request.META.get("REMOTE_ADDR")


def invalidate_all_user_sessions(user):
    """Delete all active sessions belonging to this user.

    Goes through the configured session backend's SessionStore.delete()
    (not Session.delete() on the model directly) so that under
    SESSION_ENGINE=cached_db the per-process cache entry is evicted too --
    a raw model delete only removes the DB row, leaving any worker that
    already cached this session free to keep treating it as valid for up to
    SESSION_COOKIE_AGE.
    """
    session_store_cls = import_module(settings.SESSION_ENGINE).SessionStore
    active_sessions = Session.objects.filter(expire_date__gte=timezone.now())

    for session in active_sessions:
        data = session.get_decoded()

        if str(user.id) == str(data.get("_auth_user_id")):
            session_store_cls(session_key=session.session_key).delete()


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
