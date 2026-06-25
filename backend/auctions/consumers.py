"""Channels consumer for live bid updates."""
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger("securebid")


def _group_name(listing_id: str) -> str:
    """Stable channel group name for a listing."""
    return f"auction_{listing_id}"


class BidConsumer(AsyncJsonWebsocketConsumer):
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

        self.listing_id = str(self.scope["url_route"]["kwargs"]["listing_id"])
        self.group = _group_name(self.listing_id)

        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def bid_update(self, event):
        """Relay a group message to this WebSocket client."""
        await self.send_json(event["data"])
