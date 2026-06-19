"""Auction listing and bid models for SecureBid."""
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Listing(models.Model):
    """An auction item listing created and managed by an admin."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("active", "Active"),
        ("ended", "Ended"),
        ("cancelled", "Cancelled"),
    ]

    OPENING_SOON_WINDOW = timedelta(days=1)

    CATEGORY_CHOICES = [
        ("Handbag", "Handbag"),
        ("Watches", "Watches"),
        ("Perfumes", "Perfumes"),
        ("Fashion & Apparel", "Fashion & Apparel"),
        ("Accessories", "Accessories"),
        ("Fine Art & Collectibles", "Fine Art & Collectibles"),
        ("Wines & Spirits", "Wines & Spirits"),
        ("Home Decor & Furniture", "Home Decor & Furniture"),
        ("Others", "Others"),
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
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default="Others",
    )
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

    @classmethod
    def determine_status(cls, starts_at, ends_at, now=None):
        now = now or timezone.now()

        if ends_at and now >= ends_at:
            return "ended"
        if starts_at and now >= starts_at:
            return "active"
        return "scheduled"

    def get_runtime_status(self, now=None):
        now = now or timezone.now()

        if self.status in {"draft", "cancelled"}:
            return self.status

        return self.determine_status(self.starts_at, self.ends_at, now=now)

    def get_display_status(self, now=None):
        now = now or timezone.now()

        runtime_status = self.get_runtime_status(now=now)

        if runtime_status == "draft":
            return "Draft"
        if runtime_status == "cancelled":
            return "Cancelled"

        if runtime_status == "ended":
            return "Ended"

        if runtime_status == "active":
            return "Live Now"

        if self.starts_at and self.starts_at - now <= self.OPENING_SOON_WINDOW:
            return "Opening Soon"

        return "Scheduled"

    def save(self, *args, **kwargs):
        if self.status not in {"draft", "cancelled"}:
            self.status = self.determine_status(self.starts_at, self.ends_at)
        super().save(*args, **kwargs)

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
