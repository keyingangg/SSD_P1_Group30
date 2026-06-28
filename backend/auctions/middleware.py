"""ASGI middleware for WebSocket Origin validation (SFR-08d / AR-07)."""
import logging

from django.conf import settings

logger = logging.getLogger("securebid")


class OriginValidationMiddleware:
    """Reject WebSocket upgrade requests whose Origin header is not in
    ``CORS_ALLOWED_ORIGINS``."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            headers = dict(scope.get("headers", []))
            origin = headers.get(b"origin", b"").decode()
            allowed = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
            if not origin or origin not in allowed:
                logger.warning("WebSocket origin rejected: %s", origin)
                await send({"type": "websocket.close", "code": 4004})
                return
        await self.app(scope, receive, send)
