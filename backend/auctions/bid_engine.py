"""Core bidding engine: validation, locking, and atomic commit."""

import logging
from decimal import Decimal, InvalidOperation

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.exceptions import PermissionDenied
from django.db import OperationalError, transaction
from django.utils import timezone

from core.audit import log_action, device_fingerprint as _device_fingerprint
from .models import Bid, Listing

logger = logging.getLogger("securebid")


def _broadcast_bid(
    listing_id: str,
    bid_id: str,
    amount: str,
    anonymous_identifier: str,
    submitted_at: str,
    is_winning: bool,
) -> None:
    """Push an anonymised bid-update message to all WebSocket viewers of a listing.

    Sends exactly one message per bid so the frontend never sees duplicates.
    bidder_id is intentionally omitted (NFSR-C-04 / SFR-11f).
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.warning("No channel layer configured — skipping bid broadcast for listing %s", listing_id)
        return
    group = f"auction_{listing_id}"
    async_to_sync(channel_layer.group_send)(
        group,
        {
            "type": "bid_update",
            "data": {
                "event": "bid_placed",
                "bid_id": bid_id,
                "listing_id": listing_id,
                "amount": amount,
                "current_highest_bid": amount,
                "anonymous_identifier": anonymous_identifier,
                "submitted_at": submitted_at,
                "is_winning": is_winning,
            },
        },
    )


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

        if Bid.objects.filter(listing=listing, bidder=user, is_winning=True).exists():
            raise ValueError("You cannot place consecutive bids — you are already the highest bidder.")

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
                device_fingerprint=_device_fingerprint(ip_address, user_agent),
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

    # Broadcast outside the atomic block so clients only see committed state (NFR-02)
    _broadcast_bid(
        listing_id=str(listing_id),
        bid_id=str(bid.id),
        amount=str(bid_amount),
        anonymous_identifier=anonymous_identifier,
        submitted_at=bid.submitted_at.isoformat(),
        is_winning=bid.is_winning,
    )

    return bid, listing
