"""Serializers for the payments app."""
from rest_framework import serializers


class CreatePaymentIntentSerializer(serializers.Serializer):
    """Validate a request to create a payment intent for an order."""

    order_id = serializers.UUIDField()
    # Optional: the winner may supply/confirm a delivery address at checkout.
    delivery_address = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        trim_whitespace=True,
    )


class UpdateFulfillmentSerializer(serializers.Serializer):
    """Validate an admin fulfilment-status update."""

    fulfillment_status = serializers.CharField(max_length=20)
