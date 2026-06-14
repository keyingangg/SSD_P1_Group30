"""Serializers for the auctions app."""
from rest_framework import serializers


class ListingSerializer(serializers.Serializer):
    """Serialize a listing for public/detail views (no bidder identities)."""

    # TODO: expose safe listing fields, anonymised highest bid.
    pass


class BidSerializer(serializers.Serializer):
    """Serialize a bid for display using only the anonymised identifier."""

    # TODO: expose anonymous_identifier, amount, submitted_at.
    pass


class BidSubmitSerializer(serializers.Serializer):
    """Validate an incoming bid submission (amount only)."""

    # TODO: define amount field; all validation re-checked server-side.
    pass
