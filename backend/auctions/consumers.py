"""Channels consumer for live bid updates.

AuthMiddlewareStack re-reads the Django session on every new WebSocket
handshake, so reconnections always re-verify authentication and email
verification status (FSR-AZ-08).
"""
import logging
import time
from collections import defaultdict

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger("securebid")

# Close codes (4000-4999 range is available for application use).
WS_CLOSE_UNAUTHENTICATED = 4001
WS_CLOSE_READ_ONLY = 4002
WS_CLOSE_EMAIL_UNVERIFIED = 4003
WS_CLOSE_ORIGIN_REJECTED = 4004
WS_CLOSE_RATE_LIMITED = 4029


CATALOGUE_GROUP = "catalogue"


def _group_name(listing_id: str) -> str:
    """Stable channel group name for a listing."""
    return f"auction_{listing_id}"


class CatalogueConsumer(AsyncJsonWebsocketConsumer):
    """Broadcasts catalogue-level events (new listings, status changes) to all viewers."""

    async def connect(self):
        await self.channel_layer.group_add(CATALOGUE_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(CATALOGUE_GROUP, self.channel_name)

    async def catalogue_update(self, event):
        await self.send_json(event["data"])


class BidConsumer(AsyncJsonWebsocketConsumer):
    """Broadcasts anonymised live bid updates to viewers of an auction.

    This consumer is read-only — clients cannot send messages. Bids are
    submitted via the REST API; successful bids trigger a ``group_send``
    from the view layer.
    """

    _connect_log: dict[str, list[float]] = defaultdict(list)
    MAX_CONNECTS = 10
    WINDOW_SECONDS = 60

    async def connect(self):
        # --- Rate limiting (NFSR-AV-03) ---
        user = self.scope.get("user")
        if user and getattr(user, "is_authenticated", False):
            rate_key = str(user.pk)
        else:
            rate_key = self.scope.get("client", ("unknown",))[0]

        now = time.time()
        log = self._connect_log[rate_key]
        self._connect_log[rate_key] = [t for t in log if now - t < self.WINDOW_SECONDS]
        if len(self._connect_log[rate_key]) >= self.MAX_CONNECTS:
            logger.warning("WebSocket rate limited key=%s", rate_key)
            await self.accept()
            await self.close(code=WS_CLOSE_RATE_LIMITED)
            return
        self._connect_log[rate_key].append(now)

        # --- Authentication (SFR-08a / NFSR-AZ-04) ---
        if not user or not user.is_authenticated:
            logger.warning(
                "WebSocket connect denied: unauthenticated scope=%s path=%s",
                user, self.scope.get("path"),
            )
            await self.accept()
            await self.close(code=WS_CLOSE_UNAUTHENTICATED)
            return

        if not getattr(user, "is_email_verified", False):
            logger.warning(
                "WebSocket connect denied: email unverified user=%s", user.pk,
            )
            await self.accept()
            await self.close(code=WS_CLOSE_EMAIL_UNVERIFIED)
            return

        self.listing_id = str(self.scope["url_route"]["kwargs"]["listing_id"])
        self.group = _group_name(self.listing_id)

        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # WebSocket is broadcast-only; reject any client-sent messages (SFR-08b).
        await self.close(code=WS_CLOSE_READ_ONLY)

    async def bid_update(self, event):
        """Relay a bid update to this WebSocket client."""
        await self.send_json(event["data"])

    async def auction_closed(self, event):
        """Relay an auction-close event (cancelled or ended) to this WebSocket client."""
        await self.send_json(event["data"])
