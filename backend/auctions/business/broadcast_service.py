"""Catalogue Broadcast Service (diagram: business-layer box).

Pushes catalogue-changed events to WebSocket viewers so the listing feed
updates live when an admin creates, edits, or cancels a listing.
"""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_catalogue_update():
    """Push a catalogue-changed event via the channel layer.

    No-op when the channel layer is not configured (e.g. plain WSGI runserver).
    Exceptions are swallowed so a missing channel layer never breaks REST calls.
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            "catalogue",
            {"type": "catalogue.update", "data": {"event": "catalogue_changed"}},
        )
    except Exception:
        pass
