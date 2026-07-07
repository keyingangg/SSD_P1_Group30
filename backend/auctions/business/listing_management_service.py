"""Listing Management Service (diagram: business-layer box, Admin frame).

Owns admin-only listing lifecycle operations -- create, update, delete,
cancel -- and the active-listing summary used by the Admin Overview API.
Shared by the Listing Manage API and the Admin Overview API.
"""
from decimal import Decimal

from ..data.models import Bid, Listing


class ListingActionBlocked(Exception):
    """Raised when an admin action is blocked by listing state (SFR-06c)."""


def create_listing(data, created_by):
    """Create a new listing. Returns (listing, save_as_draft)."""
    img_key = data.get("image_key")
    if isinstance(img_key, str) and img_key.strip() == "":
        img_key = None

    starts_at = data.get("starts_at")
    ends_at = data.get("ends_at")
    minimum_increment = data.get("minimum_increment") or Decimal("1.00")
    save_as_draft = data.get("save_as_draft", False)

    listing = Listing.objects.create(
        created_by=created_by,
        title=data["title"],
        description=data.get("description", ""),
        image_key=img_key,
        category=data.get("category", "Others"),
        starting_price=data.get("starting_price") or Decimal("0.00"),
        minimum_increment=minimum_increment,
        starts_at=starts_at,
        ends_at=ends_at,
        status="draft" if save_as_draft else Listing.determine_status(starts_at, ends_at),
    )
    return listing, save_as_draft


def _snapshot(listing):
    return {
        "title": listing.title,
        "description": listing.description,
        "category": listing.category,
        "starting_price": str(listing.starting_price),
        "minimum_increment": str(listing.minimum_increment),
        "starts_at": listing.starts_at.isoformat() if listing.starts_at else None,
        "ends_at": listing.ends_at.isoformat() if listing.ends_at else None,
        "status": listing.status,
    }


def update_listing(listing, data):
    """Apply admin edits. Returns (before, after, save_as_draft).

    Raises ListingActionBlocked if bids already exist (and the listing isn't
    already cancelled), or if the auction is live and the caller isn't
    saving as a draft.
    """
    has_bids = listing.bids.exists()
    saving_as_draft = data.get("save_as_draft", False)

    if has_bids and listing.status != "cancelled":
        raise ListingActionBlocked(
            "This listing cannot be modified because bids have already been placed. "
            "Cancel the auction first, then make changes."
        )
    if listing.status == "active" and not saving_as_draft:
        raise ListingActionBlocked(
            "This listing cannot be modified while the auction is live. Cancel it first."
        )

    before_snapshot = _snapshot(listing)

    listing.title = data["title"]
    listing.description = data.get("description", listing.description)
    listing.category = data.get("category", listing.category)
    listing.image_key = data.get("image_key", listing.image_key)
    listing.starting_price = data.get("starting_price") or listing.starting_price or Decimal("0.00")
    listing.minimum_increment = data.get("minimum_increment", listing.minimum_increment)
    listing.starts_at = data.get("starts_at", listing.starts_at)
    listing.ends_at = data.get("ends_at", listing.ends_at)

    if listing.status == "cancelled":
        pass
    elif saving_as_draft:
        listing.status = "draft"
    else:
        listing.status = Listing.determine_status(listing.starts_at, listing.ends_at)

    listing.save()

    return before_snapshot, _snapshot(listing), saving_as_draft


def assert_can_delete(listing):
    """Raise ListingActionBlocked if deletion should be refused (SFR-06c)."""
    if listing.bids.exists() and listing.status != "cancelled":
        raise ListingActionBlocked(
            "This listing cannot be deleted because bids have already been placed. "
            "Cancel the auction first, then delete it."
        )


def cancel_listing(listing):
    """Cancel an auction. Returns the unique bidder emails to notify."""
    bidder_emails = list(
        Bid.objects.filter(listing=listing)
        .select_related("bidder")
        .values_list("bidder__email", flat=True)
        .distinct()
    )
    listing.status = "cancelled"
    listing.save(update_fields=["status", "updated_at"])
    return bidder_emails


def get_active_listings_summary(now, limit=10):
    """Active listing count/list plus today's bid count, for the Admin Overview API."""
    active_listings = Listing.objects.filter(status="active")
    bids_today = Bid.objects.filter(submitted_at__date=now.date()).count()
    upcoming = [
        {
            "id": str(listing.id),
            "lot": str(listing.id)[:8].upper(),
            "name": listing.title,
            "bid": str(listing.current_highest_bid),
            "ends_at": listing.ends_at.isoformat() if listing.ends_at else None,
        }
        for listing in active_listings.order_by("ends_at")[:limit]
    ]
    return active_listings.count(), bids_today, upcoming
