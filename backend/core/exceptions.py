"""Custom DRF exception handling."""
import logging

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
    """
    response = exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled exception in %s", context.get("view"))
        return Response(
            {"detail": "An error occurred. Please try again."},
            status=500,
        )

    return response
