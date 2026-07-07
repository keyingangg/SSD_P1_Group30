"""Catalogue WebSocket consumer (diagram: svc_catalogue_ws)."""
from channels.generic.websocket import AsyncJsonWebsocketConsumer

CATALOGUE_GROUP = "catalogue"


class CatalogueConsumer(AsyncJsonWebsocketConsumer):
    """Broadcasts catalogue-level events (new listings, status changes) to all viewers."""

    async def connect(self):
        await self.channel_layer.group_add(CATALOGUE_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(CATALOGUE_GROUP, self.channel_name)

    async def catalogue_update(self, event):
        await self.send_json(event["data"])
