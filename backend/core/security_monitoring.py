"""Real-time threshold detection for denied-authorisation bursts (FSR-AC-07).

Counts AUTHZ_DENIED events per account and per IP in a rolling window using
Django's cache framework. When either counter reaches the configured
threshold, fires one security alert for that window (a companion "alerted"
flag suppresses repeat alerts on every subsequent denial until the window
expires).
"""
import logging

from django.conf import settings
from django.core.cache import cache

from .alerts import send_security_alert
from .audit import log_action

logger = logging.getLogger("securebid")


def _bump_and_check(kind: str, key_value, *, window: int, threshold: int) -> int:
    cache_key = f"authz_denied:{kind}:{key_value}"
    try:
        count = cache.incr(cache_key)
    except ValueError:
        # Key does not exist yet (first denial in this window).
        cache.set(cache_key, 1, timeout=window)
        count = 1
    return count


def record_authz_denial(user, ip_address, *, view_name: str = "", endpoint_path: str = ""):
    """Record a denied-authorisation event and alert on threshold breach.

    Called from RBACMiddleware for every AUTHZ_DENIED event, in addition to
    (not instead of) the individual AuditLog entry already written there.
    """
    threshold = settings.AUTHZ_DENIAL_ALERT_THRESHOLD
    window = settings.AUTHZ_DENIAL_ALERT_WINDOW_SECONDS

    user_id = getattr(user, "id", None) if getattr(user, "is_authenticated", False) else None

    candidates = []
    if user_id:
        candidates.append(("account", str(user_id)))
    if ip_address:
        candidates.append(("ip", ip_address))

    for kind, key_value in candidates:
        try:
            count = _bump_and_check(kind, key_value, window=window, threshold=threshold)
        except Exception:
            logger.exception("Failed to update authz denial counter for %s=%s", kind, key_value)
            continue

        if count < threshold:
            continue

        # Only fire once per window: the "alerted" flag is set with cache.add,
        # which is atomic and only succeeds for the first caller to reach it.
        alerted_key = f"authz_denied_alerted:{kind}:{key_value}"
        if not cache.add(alerted_key, True, timeout=window):
            continue

        try:
            send_security_alert(
                subject="Repeated denied authorisation attempts",
                message=(
                    f"{count} denied authorisation attempts from {kind}={key_value} "
                    f"within {window} seconds (threshold: {threshold})."
                ),
                severity="high",
                metadata={
                    kind: key_value,
                    "denial_count": count,
                    "window_seconds": window,
                    "view": view_name,
                    "endpoint_path": endpoint_path,
                },
            )
            log_action(
                user=user if getattr(user, "is_authenticated", False) else None,
                action="authz_anomaly_detected",
                resource_type=kind,
                ip_address=ip_address if kind == "ip" else None,
                endpoint_path=endpoint_path,
                metadata={"denial_count": count, "window_seconds": window, "view": view_name},
            )
        except Exception:
            logger.exception("Failed to alert on authz denial burst for %s=%s", kind, key_value)
