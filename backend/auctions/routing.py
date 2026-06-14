"""WebSocket URL routing for the auctions app."""
from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path(
        "ws/auctions/<uuid:listing_id>/",
        consumers.BidConsumer.as_asgi(),
    ),
]
