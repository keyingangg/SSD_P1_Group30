"""Channels consumer for live bid updates."""
from channels.generic.websocket import AsyncWebsocketConsumer


class BidConsumer(AsyncWebsocketConsumer):
    """Broadcasts anonymised live bid updates to viewers of an auction."""

    async def connect(self):
        # TODO: verify authentication + email verification, validate Origin
        # (CSWSH protection), then group_add and accept.
        await self.accept()

    async def disconnect(self, close_code):
        # TODO: group_discard from the auction group.
        pass

    async def bid_update(self, event):
        # TODO: send anonymised bid data to the client.
        pass
