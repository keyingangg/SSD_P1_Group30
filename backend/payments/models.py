"""Order and payment models for SecureBid."""
import uuid

from django.conf import settings
from django.db import models


class Order(models.Model):
    """Payment and fulfilment record for a won auction (one per listing)."""

    FULFILLMENT_CHOICES = [
        ("pending_payment", "Pending Payment"),
        ("paid", "Paid"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    winning_bid = models.OneToOneField(
        "auctions.Bid", on_delete=models.PROTECT, related_name="order"
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255, blank=True, null=True
    )
    # UUID4 idempotency key prevents duplicate Stripe charges.
    stripe_idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True)
    fulfillment_status = models.CharField(
        max_length=20,
        choices=FULFILLMENT_CHOICES,
        default="pending_payment",
    )
    delivery_address_snapshot = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"

    def __str__(self):
        return f"Order {self.id} ({self.fulfillment_status})"
