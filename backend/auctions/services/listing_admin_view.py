"""Listing management API for admins (diagram: svc_listing_admin)."""
import logging
from decimal import Decimal

from rest_framework.response import Response
from rest_framework.views import APIView

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from accounts.services.permissions import IsAdminUser

from core.cross_cutting.audit import log_action, device_fingerprint as _device_fingerprint
from ..business.broadcast_service import broadcast_catalogue_update
from ..business.emails import send_auction_cancelled_email
from ..data.models import Bid, Listing
from .serializers import ListingCreateSerializer

logger = logging.getLogger("securebid")


class ListingCreateView(APIView):
    """Create a new listing (admin only)."""

    permission_classes = [IsAdminUser]
    staff_only = True

    def post(self, request):

        serializer = ListingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        save_as_draft = data.get("save_as_draft", False)

        img_key = data.get("image_key")
        if isinstance(img_key, str) and img_key.strip() == "":
            img_key = None

        starts_at = data.get("starts_at")
        ends_at = data.get("ends_at")
        minimum_increment = data.get("minimum_increment") or Decimal("1.00")

        listing = Listing.objects.create(
            created_by=request.user,
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

        log_action(
            user=request.user,
            action="listing_created",
            resource_type="Listing",
            resource_id=listing.id,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            device_fingerprint=_device_fingerprint(request.META.get("REMOTE_ADDR"), request.META.get("HTTP_USER_AGENT", "")),
            request_method=request.method,
            endpoint_path=request.path,
            metadata={"listing_title": listing.title, "save_as_draft": save_as_draft},
        )

        if not save_as_draft:
            broadcast_catalogue_update()

        return Response({"detail": "Listing created.", "id": listing.id, "image_key": listing.image_key}, status=201)


class ListingUpdateView(APIView):
    """Update an existing listing (admin only).

    Modification is blocked once any bid has been placed -- the auction must be
    cancelled first (SFR-06c).
    """

    permission_classes = [IsAdminUser]
    staff_only = True

    def patch(self, request, listing_id):

        try:
            listing = Listing.objects.get(pk=listing_id)
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found."}, status=404)

        has_bids = listing.bids.exists()
        saving_as_draft = request.data.get("save_as_draft", False)

        # Bids have been placed -- no further changes allowed (except on cancelled listings)
        if has_bids and listing.status != "cancelled":
            return Response(
                {"detail": "This listing cannot be modified because bids have already been placed. Cancel the auction first, then make changes."},
                status=409,
            )

        # Active (live) auction with no bids: allow save-as-draft to pull it back,
        # but block re-publishing (admins must cancel first to change the schedule).
        if listing.status == "active" and not saving_as_draft:
            return Response(
                {"detail": "This listing cannot be modified while the auction is live. Cancel it first."},
                status=409,
            )

        serializer = ListingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        save_as_draft = data.get("save_as_draft", False)

        # Capture state before modification for the audit trail (NFSR-AC-03).
        before_snapshot = {
            "title": listing.title,
            "description": listing.description,
            "category": listing.category,
            "starting_price": str(listing.starting_price),
            "minimum_increment": str(listing.minimum_increment),
            "starts_at": listing.starts_at.isoformat() if listing.starts_at else None,
            "ends_at": listing.ends_at.isoformat() if listing.ends_at else None,
            "status": listing.status,
        }

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
        elif save_as_draft:
            listing.status = "draft"
        else:
            listing.status = Listing.determine_status(listing.starts_at, listing.ends_at)

        listing.save()

        after_snapshot = {
            "title": listing.title,
            "description": listing.description,
            "category": listing.category,
            "starting_price": str(listing.starting_price),
            "minimum_increment": str(listing.minimum_increment),
            "starts_at": listing.starts_at.isoformat() if listing.starts_at else None,
            "ends_at": listing.ends_at.isoformat() if listing.ends_at else None,
            "status": listing.status,
        }

        log_action(
            user=request.user,
            action="listing_updated",
            resource_type="Listing",
            resource_id=listing.id,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            device_fingerprint=_device_fingerprint(request.META.get("REMOTE_ADDR"), request.META.get("HTTP_USER_AGENT", "")),
            role="staff" if request.user.is_staff else "user",
            before=before_snapshot,
            after=after_snapshot,
            request_method=request.method,
            endpoint_path=request.path,
            metadata={"save_as_draft": save_as_draft},
        )

        if not save_as_draft:
            broadcast_catalogue_update()

        return Response({"detail": "Listing updated."}, status=200)


class ListingDeleteView(APIView):
    """Delete a listing (admin only).

    Deletion is blocked once any bid has been placed -- the auction must be
    cancelled first (SFR-06c).
    """

    permission_classes = [IsAdminUser]
    staff_only = True

    def delete(self, request, listing_id):

        try:
            listing = Listing.objects.get(pk=listing_id)
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found."}, status=404)

        # SFR-06c: prevent deletion of a listing that has received bids
        # unless the auction has already been cancelled.
        if listing.bids.exists() and listing.status != "cancelled":
            return Response(
                {
                    "detail": (
                        "This listing cannot be deleted because bids have already been placed. "
                        "Cancel the auction first, then delete it."
                    )
                },
                status=409,
            )

        log_action(
            user=request.user,
            action="listing_deleted",
            resource_type="Listing",
            resource_id=listing.id,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            device_fingerprint=_device_fingerprint(request.META.get("REMOTE_ADDR"), request.META.get("HTTP_USER_AGENT", "")),
            request_method=request.method,
            endpoint_path=request.path,
            metadata={"listing_title": listing.title},
        )
        listing.delete()
        return Response(status=204)


class ListingCancelView(APIView):
    """Cancel an auction and notify all bidders (SFR-06c).

    Once cancelled the listing is locked: bidding stops and the admin may
    then modify or delete it. Every unique bidder is emailed so they know
    their bids are void.
    """

    permission_classes = [IsAdminUser]
    staff_only = True

    def post(self, request, listing_id):
        try:
            listing = Listing.objects.get(pk=listing_id)
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found."}, status=404)

        if listing.status == "cancelled":
            return Response({"detail": "Listing is already cancelled."}, status=400)

        # Collect unique bidder emails before status change.
        bidder_emails = list(
            Bid.objects.filter(listing=listing)
            .select_related("bidder")
            .values_list("bidder__email", flat=True)
            .distinct()
        )

        listing.status = "cancelled"
        listing.save(update_fields=["status", "updated_at"])

        # Notify every bidder whose bids are now void.
        notified = 0
        for email in bidder_emails:
            try:
                send_auction_cancelled_email(email, listing)
                notified += 1
            except Exception:
                logger.error(
                    "Failed to send auction-cancellation email to %s for listing %s",
                    email,
                    listing_id,
                )

        log_action(
            user=request.user,
            action="listing_cancelled",
            resource_type="Listing",
            resource_id=listing.id,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            device_fingerprint=_device_fingerprint(request.META.get("REMOTE_ADDR"), request.META.get("HTTP_USER_AGENT", "")),
            metadata={
                "listing_title": listing.title,
                "bidders_notified": notified,
                "total_bidders": len(bidder_emails),
            },
        )

        # Broadcast cancellation to listing viewers and catalogue
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"auction_{listing.id}",
                {
                    "type": "auction.closed",
                    "data": {"event": "auction_cancelled", "status": "cancelled"},
                },
            )
        broadcast_catalogue_update()

        return Response(
            {
                "detail": "Auction cancelled.",
                "bidders_notified": notified,
            },
            status=200,
        )
