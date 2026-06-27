"""Channels consumer for live bid updates."""
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger("securebid")

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
    """Broadcasts anonymised live bid updates to viewers of an auction."""

    async def connect(self):
        # Bid broadcasts are public read-only — anyone viewing a listing may connect.
        # Bid submission still requires auth via the REST endpoint.
        self.listing_id = str(self.scope["url_route"]["kwargs"]["listing_id"])
        self.group = _group_name(self.listing_id)

        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def bid_update(self, event):
        """Relay a bid update to this WebSocket client."""
        await self.send_json(event["data"])

    async def auction_closed(self, event):
        """Relay an auction-close event (cancelled or ended) to this WebSocket client."""
        await self.send_json(event["data"])
