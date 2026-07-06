"""Serializers for the payments app."""
from rest_framework import serializers

from .models import Order


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
    """Validate an admin fulfilment-status update.

    Allowlist-first (NFSR-IN-03): only values defined in
    Order.FULFILLMENT_CHOICES are accepted at the serializer boundary,
    rather than relying solely on the view's later transition check.
    """

    fulfillment_status = serializers.ChoiceField(
        choices=[choice[0] for choice in Order.FULFILLMENT_CHOICES]
    )
