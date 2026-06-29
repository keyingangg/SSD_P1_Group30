"""Auction listing and bid models for SecureBid."""
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
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
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
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

        return "Scheduled"

    def save(self, *args, **kwargs):
        if self.status not in {"draft", "cancelled"}:
            self.status = self.determine_status(self.starts_at, self.ends_at)
        super().save(*args, **kwargs)

    def finalize_if_ended(self, now=None):
        """Persist winner/status once the auction has ended."""
        now = now or timezone.now()

        if self.status in {"draft", "cancelled"}:
            return False

        if not self.ends_at or now < self.ends_at:
            return False

        winning_bid = self.bids.order_by("-amount", "submitted_at", "id").first()
        winner_id = winning_bid.bidder_id if winning_bid else None

        fields_to_update = []

        if self.status != "ended":
            self.status = "ended"
            fields_to_update.append("status")

        if self.winner_id != winner_id:
            self.winner_id = winner_id
            fields_to_update.append("winner")

        if winning_bid and self.current_highest_bid != winning_bid.amount:
            self.current_highest_bid = winning_bid.amount
            fields_to_update.append("current_highest_bid")

        if fields_to_update:
            fields_to_update.append("updated_at")
            self.save(update_fields=fields_to_update)

        # Log winner selection exactly once, when the winner field is first set.
        if fields_to_update and "winner" in fields_to_update and winning_bid:
            try:
                from core.audit import log_action
                log_action(
                    user=winning_bid.bidder,
                    action="winner_selected",
                    resource_type="Listing",
                    resource_id=self.id,
                    role="user",
                    metadata={
                        "winning_bid_id": str(winning_bid.id),
                        "winning_amount": str(winning_bid.amount),
                        "listing_title": self.title,
                    },
                )
            except Exception:
                pass  # Never block auction finalization due to a logging failure.

        if winning_bid:
            self.bids.exclude(pk=winning_bid.pk).update(is_winning=False)
            if not winning_bid.is_winning:
                winning_bid.is_winning = True
                winning_bid.save(update_fields=["is_winning"])

            # Create the fulfilment Order for the winner exactly once. Keyed on
            # the winning bid (OneToOne) so repeated finalize calls — this runs
            # on many GET requests — never create duplicate orders (FR-03).
            # Imported here to avoid a circular import (payments imports Bid).
            from payments.models import Order

            Order.objects.get_or_create(
                winning_bid=winning_bid,
                defaults={
                    "winner_id": winner_id,
                    "delivery_address_snapshot": "",
                    "fulfillment_status": "pending_payment",
                },
            )

        return bool(fields_to_update)

    @classmethod
    def finalize_ended_auctions(cls, now=None):
        """Finalize all auctions that reached end time and still need winner/status sync."""
        now = now or timezone.now()

        ended_candidates = cls.objects.exclude(status__in={"draft", "cancelled"}).filter(
            ends_at__lte=now
        ).filter(Q(status__in={"active", "scheduled"}) | Q(winner__isnull=True))

        for listing in ended_candidates:
            listing.finalize_if_ended(now=now)

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
