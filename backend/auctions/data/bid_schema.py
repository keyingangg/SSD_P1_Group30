"""Bid model (diagram: data_bid)."""
import uuid

from django.conf import settings
from django.db import models

from .listing_schema import Listing


class Bid(models.Model):
    """A single bid placed on a listing."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="bids"
    )
    bidder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bids",
    )
    # Public-facing anonymised label, e.g. "Bidder #4729".
    anonymous_identifier = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    # Server-assigned timestamp; used for tie-breaking.
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_winning = models.BooleanField(default=False)

    class Meta:
        db_table = "bids"
        indexes = [
            models.Index(fields=["bidder", "submitted_at"], name="bid_bidder_submitted_idx"),
        ]

    def __str__(self):
        return f"{self.anonymous_identifier} - {self.amount}"
