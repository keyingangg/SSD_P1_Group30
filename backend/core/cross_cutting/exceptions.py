"""Custom DRF exception handling."""
import logging

from rest_framework.exceptions import UnsupportedMediaType, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("securebid")


def custom_exception_handler(exc, context):
    """Hide internal details on server errors; surface client (4xx) errors.

    DRF returns a response for handled exceptions (validation, auth, permission
    — all 4xx); those carry useful, safe messages and are passed through. An
    unhandled exception yields no DRF response (a 500); we log the full detail
    server-side and return only a generic message so stack traces, file paths,
    and configuration never reach the client (NFSR-C-05 / AR-10).

    Rate-limit breaches (Ratelimited) return 429 and are audit-logged
    (NFSR-AV-03 / SFR-11g).

    Serializer validation failures return a single generic 400 message so
    callers cannot enumerate field names or derive schema details
    (NFSR-IN-03 / FSR-IN-05).
    """
    # Rate-limit breach — 429 + audit log.
    try:
        from django_ratelimit.exceptions import Ratelimited
        if isinstance(exc, Ratelimited):
            _log_rate_limit_breach(context)
            return Response(
                {"detail": "Too many requests. Please try again later."},
                status=429,
            )
    except ImportError:
        pass

    response = exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled exception in %s", context.get("view"))
        return Response(
            {"detail": "An error occurred. Please try again."},
            status=500,
        )

    # Collapse serializer ValidationError details into a generic message so
    # field names and schema information are not exposed (NFSR-IN-03 / FSR-IN-05).
    if isinstance(exc, ValidationError) and response.status_code == 400:
        return Response({"detail": "Request validation failed."}, status=400)

    # DRF's default UnsupportedMediaType message echoes the client-supplied
    # Content-Type back into the response body; return a generic one instead
    # (FSR-IN-05).
    if isinstance(exc, UnsupportedMediaType):
        return Response({"detail": "Unsupported content type."}, status=415)

    return response


def _log_rate_limit_breach(context):
    """Write an audit log entry for a rate-limit breach (SFR-11g)."""
    try:
        from core.cross_cutting.audit import log_action

        request = context.get("request")
        view = context.get("view")
        ip = request.META.get("REMOTE_ADDR") if request else None
        user_agent = request.META.get("HTTP_USER_AGENT", "") if request else ""
        user = getattr(request, "user", None)
        if user is not None and not user.is_authenticated:
            user = None

        log_action(
            user=user,
            action="rate_limit_exceeded",
            resource_type=view.__class__.__name__ if view else "unknown",
            ip_address=ip,
            user_agent=user_agent,
            metadata={"endpoint": view.__class__.__name__ if view else "unknown"},
        )
    except Exception:
        logger.exception("Failed to write rate-limit audit log entry")
