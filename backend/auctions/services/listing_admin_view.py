"""Listing management API for admins (diagram: svc_listing_admin)."""
import logging

from rest_framework.response import Response
from rest_framework.views import APIView

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from accounts.services.permissions import IsAdminUser

from core.cross_cutting.audit import log_action, device_fingerprint as _device_fingerprint
from ..business.broadcast_service import broadcast_catalogue_update
from ..business.emails import send_auction_cancelled_email
from ..business.listing_management_service import (
    ListingActionBlocked,
    assert_can_delete,
    cancel_listing,
    create_listing,
    update_listing,
)
from ..data.models import Listing
from .serializers import ListingCreateSerializer

logger = logging.getLogger("securebid")


class ListingCreateView(APIView):
    """Create a new listing (admin only)."""

    permission_classes = [IsAdminUser]
    staff_only = True

    def post(self, request):

        serializer = ListingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        listing, save_as_draft = create_listing(serializer.validated_data, request.user)

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

        serializer = ListingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            before_snapshot, after_snapshot, save_as_draft = update_listing(
                listing, serializer.validated_data
            )
        except ListingActionBlocked as exc:
            return Response({"detail": str(exc)}, status=409)

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

        try:
            assert_can_delete(listing)
        except ListingActionBlocked as exc:
            return Response({"detail": str(exc)}, status=409)

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

        bidder_emails = cancel_listing(listing)

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
