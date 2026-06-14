"""Auction listing and bid models for SecureBid."""
import uuid

from django.conf import settings
from django.db import models


class Listing(models.Model):
    """An auction item listing created and managed by an admin."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("active", "Active"),
        ("closed", "Closed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_listings",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    # Filename reference for the image stored in Supabase Storage.
    image_key = models.CharField(max_length=512, null=True, blank=True)
    starting_price = models.DecimalField(max_digits=12, decimal_places=2)
    current_highest_bid = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    minimum_increment = models.DecimalField(max_digits=12, decimal_places=2)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
    )
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="won_listings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "listings"

    def __str__(self):
        return self.title


class Bid(models.Model):
    """A single bid placed on a listing."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="bids"
    )
    bidder = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bids"
    )
    # Public-facing anonymised label, e.g. "Bidder #4729".
    anonymous_identifier = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    # Server-assigned timestamp; used for tie-breaking.
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_winning = models.BooleanField(default=False)

    class Meta:
        db_table = "bids"

    def __str__(self):
        return f"{self.anonymous_identifier} - {self.amount}"
