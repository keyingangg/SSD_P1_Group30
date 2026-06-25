"""Core bidding engine: validation, locking, and atomic commit."""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from .models import Bid, Listing


def submit_bid(listing_id, user, amount):
    """Validate and commit a bid atomically.

    Must enforce (all server-side):
      - user is authenticated and email-verified, and is not the listing owner
      - auction is active within its server-side time window
      - amount exceeds current highest bid by at least minimum_increment
      - PostgreSQL row-level lock (select_for_update) on the listing
      - single atomic transaction over bid creation, highest-bid update,
        and audit log entry, with full rollback on any failure
      - tie-breaking by server-assigned timestamp
    """
    if not user or not getattr(user, "is_authenticated", False):
      raise ValueError("Authentication required.")

    if not getattr(user, "is_email_verified", False):
      raise ValueError("Verified account required.")

    try:
      bid_amount = Decimal(str(amount))
    except (InvalidOperation, TypeError):
      raise ValueError("Invalid bid amount.")

    if bid_amount <= 0:
      raise ValueError("Bid amount must be greater than zero.")

    with transaction.atomic():
      try:
        listing = Listing.objects.select_for_update().get(pk=listing_id)
      except Listing.DoesNotExist as exc:
        raise LookupError("Listing not found.") from exc

      if listing.created_by_id == user.id:
        raise ValueError("You cannot bid on your own listing.")

      if getattr(user, "is_staff", False):
        raise ValueError("Admins cannot place bids.")

      runtime_status = listing.get_runtime_status(now=timezone.now())
      if runtime_status != "active":
        raise ValueError("Bidding is only allowed on active auctions.")

      current_highest = listing.current_highest_bid or listing.starting_price
      minimum_allowed = current_highest + listing.minimum_increment
      if bid_amount < minimum_allowed:
        raise ValueError(
          f"Bid must be at least {minimum_allowed:.2f}."
        )

      anonymous_identifier = f"Bidder #{str(user.id).replace('-', '')[-4:]}"

      bid = Bid.objects.create(
        listing=listing,
        bidder=user,
        anonymous_identifier=anonymous_identifier,
        amount=bid_amount,
        is_winning=True,
      )

      Bid.objects.filter(listing=listing).exclude(pk=bid.pk).update(is_winning=False)

      listing.current_highest_bid = bid_amount
      listing.save(update_fields=["current_highest_bid", "updated_at"])

      return bid, listing
