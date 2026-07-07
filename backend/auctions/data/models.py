"""Aggregates the Data Layer schema modules so Django migrations/autodiscovery
see one auctions.data.models namespace, while each schema (diagram box)
lives in its own file."""
from .listing_schema import Listing  # noqa: F401
from .bid_schema import Bid  # noqa: F401
