"""Channels consumer for live bid updates."""
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger("securebid")


class BidConsumer(AsyncWebsocketConsumer):
    """Broadcasts anonymised live bid updates to viewers of an auction."""

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated or not getattr(user, "is_email_verified", False):
            logger.warning(
                "WebSocket connect denied for unauthenticated/unverified user scope=%s path=%s",
                user,
                self.scope.get("path"),
            )
            await self.close(code=4003)
            return

        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def bid_update(self, event):
        await self.send_json(event["data"])
