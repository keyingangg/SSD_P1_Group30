"""Listing Service (diagram: business-layer box, User frame).

Owns the read-side listing lifecycle: auto-transitioning scheduled/ended
auctions and building the public browse/detail query. Shared by the Listing
API and the User Dashboard API.
"""
from django.db.models import Count
from django.utils import timezone

from ..data.models import Listing


def finalize_ended_auctions(now=None):
    """Finalize any auctions whose end time has passed."""
    Listing.finalize_ended_auctions(now=now)


def finalize_and_activate_listings(now=None):
    """Finalize ended auctions and activate scheduled ones that have started."""
    now = now or timezone.now()
    finalize_ended_auctions(now=now)
    Listing.objects.filter(
        status="scheduled", starts_at__lte=now, ends_at__gt=now
    ).update(status="active")


def search_listings(params, is_staff):
    """Build the filtered, ordered queryset for the public listing browse API."""
    queryset = Listing.objects.annotate(_bid_count=Count("bids"))
    if not is_staff:
        queryset = queryset.exclude(status__in=["draft", "cancelled", "scheduled"])

    if params.get("q"):
        queryset = queryset.filter(title__icontains=params["q"])
    if params.get("category"):
        queryset = queryset.filter(category=params["category"])
    if params.get("status"):
        queryset = queryset.filter(status=params["status"])
    if params.get("min_price") is not None:
        queryset = queryset.filter(current_highest_bid__gte=params["min_price"])
    if params.get("max_price") is not None:
        queryset = queryset.filter(current_highest_bid__lte=params["max_price"])
    return queryset.order_by(params.get("ordering", "-starts_at"))


def is_visible_to(listing, is_staff):
    """Whether a non-public-status listing may be viewed by this caller."""
    return is_staff or listing.status not in {"draft", "cancelled", "scheduled"}
