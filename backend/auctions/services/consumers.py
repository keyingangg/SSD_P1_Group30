"""Aggregates the Services Layer WebSocket consumer modules so
auctions.routing sees one auctions.services.consumers namespace, while
each consumer (diagram box) lives in its own file."""
from .catalogue_consumer import CATALOGUE_GROUP, CatalogueConsumer  # noqa: F401
from .bid_consumer import (  # noqa: F401
    WS_CLOSE_AUCTION_ENDED,
    WS_CLOSE_EMAIL_UNVERIFIED,
    WS_CLOSE_ORIGIN_REJECTED,
    WS_CLOSE_RATE_LIMITED,
    WS_CLOSE_READ_ONLY,
    WS_CLOSE_UNAUTHENTICATED,
    BidConsumer,
)
