"""
ASGI config for the SecureBid project.

Routes HTTP traffic to the standard Django application and WebSocket traffic
to the Channels consumer stack (live bid updates).
"""
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "securebid.settings.development")

# Initialise Django ASGI application early to populate the app registry
# before importing code that may import models.
django_asgi_app = get_asgi_application()

from auctions.cross_cutting.middleware import OriginValidationMiddleware  # noqa: E402
from auctions.services.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            OriginValidationMiddleware(URLRouter(websocket_urlpatterns))
        ),
    }
)
