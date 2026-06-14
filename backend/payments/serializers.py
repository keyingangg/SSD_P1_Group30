"""Serializers for the payments app."""
from rest_framework import serializers


class OrderSerializer(serializers.Serializer):
    """Serialize an order for the winning user / admin."""

    # TODO: expose order fields scoped to the requesting role.
    pass


class CreatePaymentIntentSerializer(serializers.Serializer):
    """Validate a request to create a payment intent for an order."""

    # TODO: define order_id field; verify caller is the order winner.
    pass
