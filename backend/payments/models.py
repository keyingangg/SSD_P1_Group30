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
    # Direct auction reference (auction ID, NFSR-AC-07 · FSR-AC-10). PROTECT so
    # a payment record always resolves the listing it was charged for.
    listing = models.ForeignKey(
        "auctions.Listing",
        on_delete=models.PROTECT,
        related_name="orders",
        null=True,
    )
    # Self-contained financial record: amount/currency are persisted at Order
    # creation rather than recomputed, so the row independently proves what was
    # charged (NFSR-AC-07 · FSR-AC-10).
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    currency = models.CharField(max_length=10, null=True)
    # Captured at checkout for the payment audit trail (nullable: unknown at
    # Order creation; session_key may be absent under token auth).
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    session_id = models.CharField(max_length=40, blank=True, null=True)
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
