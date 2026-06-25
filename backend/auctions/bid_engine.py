"""Core bidding engine: validation, locking, and atomic commit."""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied
from django.db import OperationalError, transaction
from django.utils import timezone

from core.audit import log_action
from .models import Bid, Listing


def submit_bid(listing_id, user, amount, ip_address=None, user_agent=""):
    """Validate and commit a bid atomically.

    Enforces (all server-side):
      - user is authenticated, email-verified, not the listing owner, not staff
      - auction is active within its server-side UTC time window
      - amount exceeds current highest bid by at least minimum_increment
      - PostgreSQL row-level lock via select_for_update(nowait=True); raises
        OperationalError if lock cannot be acquired (caller maps to HTTP 409)
      - single atomic transaction covering bid creation, highest-bid update,
        and audit log entry — full rollback on any failure
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

    user_role = "staff" if getattr(user, "is_staff", False) else "user"

    with transaction.atomic():
        try:
            listing = Listing.objects.select_for_update(nowait=True).get(pk=listing_id)
        except Listing.DoesNotExist as exc:
            raise LookupError("Listing not found.") from exc
        # OperationalError (lock not acquired) propagates to the view → HTTP 409

        if listing.created_by_id == user.id:
            raise PermissionDenied("You cannot bid on your own listing.")

        if getattr(user, "is_staff", False):
            raise PermissionDenied("Admins cannot place bids.")

        runtime_status = listing.get_runtime_status(now=timezone.now())
        if runtime_status != "active":
            raise ValueError("Bidding is only allowed on active auctions.")

        current_highest = listing.current_highest_bid or listing.starting_price
        minimum_allowed = current_highest + listing.minimum_increment
        if bid_amount < minimum_allowed:
            raise ValueError(f"Bid must be at least {minimum_allowed:.2f}.")

        anonymous_identifier = f"Bidder #{str(user.id).replace('-', '')[-4:]}"

        try:
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

            # Audit log is inside the atomic block — rolls back with the bid on failure
            log_action(
                user=user,
                action="bid_placed",
                resource_type="Bid",
                resource_id=bid.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "listing_id": str(listing.id),
                    "amount": str(bid.amount),
                    "user_role": user_role,
                },
            )
        except Exception:
            # Re-raise so transaction.atomic() rolls back all writes above.
            # The view's bare except handler logs full detail and returns HTTP 500.
            raise

        return bid, listing
