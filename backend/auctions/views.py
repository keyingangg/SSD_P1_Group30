"""API views for the auctions app."""
import logging
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db import OperationalError
from django.db.models import Count, OuterRef, Q, Subquery
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from accounts.permissions import IsAdminUser, IsEmailVerified, IsEmailVerifiedSilent
from core.audit import log_action
from core.storage import upload_image
from .bid_engine import submit_bid
from .emails import send_auction_cancelled_email
from .models import Bid, Listing
from .serializers import (
    BidSerializer,
    BidSubmitSerializer,
    ListingAdminSerializer,
    ListingCreateSerializer,
    ListingSerializer,
)

_audit_logger = logging.getLogger(__name__)


def _broadcast_catalogue_update():
    """Notify all catalogue WebSocket viewers that the listing set has changed."""
    from .consumers import CATALOGUE_GROUP
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            CATALOGUE_GROUP,
            {"type": "catalogue.update", "data": {"event": "catalogue_changed"}},
        )


class BidImmutableMixin:
    """Reject and log any DELETE or PATCH attempt on bid endpoints (NFSR-IN-05)."""

    def _reject_bid_mutation(self, request, method, **kwargs):
        user = request.user
        resource_id = kwargs.get("listing_id", "unknown")
        _audit_logger.warning(
            "Illegal bid mutation attempt: method=%s user=%s path=%s",
            method,
            getattr(user, "id", "anonymous"),
            request.path,
        )
        log_action(
            user=user if getattr(user, "is_authenticated", False) else None,
            action="bid_mutation_rejected",
            resource_type="Bid",
            resource_id=resource_id,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            metadata={
                "method": method,
                "path": request.path,
                "user_role": "staff" if getattr(user, "is_staff", False) else "user",
                "security_event": True,
            },
        )
        return Response(
            {"detail": "Bid records are immutable and cannot be modified or deleted."},
            status=405,
        )

    def delete(self, request, **kwargs):
        return self._reject_bid_mutation(request, "DELETE", **kwargs)

    def patch(self, request, **kwargs):
        return self._reject_bid_mutation(request, "PATCH", **kwargs)

logger = logging.getLogger("securebid")


@method_decorator(
    ratelimit(key="ip", rate="60/m", method="GET", block=True),
    name="get",
)
class ListingListView(APIView):
    """Browse, search, and filter published listings (public)."""

    permission_classes = [AllowAny]

    def get(self, request):
        now = timezone.now()
        Listing.finalize_ended_auctions(now=now)
        Listing.objects.filter(
            status="scheduled", starts_at__lte=now, ends_at__gt=now
        ).update(status="active")
        queryset = Listing.objects.all().order_by("-starts_at")
        if not request.user.is_staff:
            queryset = queryset.exclude(status__in=["draft", "cancelled"])
        serializer = ListingSerializer(queryset, many=True)
        return Response(serializer.data)


class ListingDetailView(APIView):
    """View a single published listing's details (public)."""

    permission_classes = [AllowAny]

    def get(self, request, listing_id):
        now = timezone.now()
        Listing.finalize_ended_auctions(now=now)
        Listing.objects.filter(
            status="scheduled", starts_at__lte=now, ends_at__gt=now
        ).update(status="active")
        try:
            listing = Listing.objects.get(pk=listing_id)
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found."}, status=404)

        if not request.user.is_staff and listing.status in {"draft", "cancelled"}:
            return Response({"detail": "Listing not found."}, status=404)

        serializer = ListingSerializer(listing)
        data = serializer.data

        if request.user.is_authenticated and not request.user.is_staff:
            user_top_bid = listing.bids.filter(bidder=request.user).order_by("-amount").first()
            winning_bid = listing.bids.filter(is_winning=True).first()
            data = dict(data)
            data["user_won"] = (
                winning_bid is not None and winning_bid.bidder_id == request.user.id
            ) or listing.winner_id == request.user.id
            data["user_highest_bid"] = str(user_top_bid.amount) if user_top_bid else None

        return Response(data)


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

        if not save_as_draft:
            _broadcast_catalogue_update()

        return Response({"detail": "Listing created.", "id": listing.id, "image_key": listing.image_key}, status=201)


class ListingUpdateView(APIView):
    """Update an existing listing (admin only).

    Modification is blocked once any bid has been placed — the auction must be
    cancelled first (SFR-06c).
    """

    permission_classes = [IsAdminUser]
    staff_only = True

    def patch(self, request, listing_id):

        try:
            listing = Listing.objects.get(pk=listing_id)
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found."}, status=404)

        if listing.status == "active":
            return Response(
                {"detail": "This listing cannot be modified while the auction is live. Cancel it first."},
                status=409,
            )
        if listing.bids.exists() and listing.status != "cancelled":
            return Response(
                {"detail": "This listing cannot be modified because bids have already been placed. Cancel the auction first, then make changes."},
                status=409,
            )

        serializer = ListingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        save_as_draft = data.get("save_as_draft", False)

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

        if not save_as_draft:
            _broadcast_catalogue_update()

        return Response({"detail": "Listing updated."}, status=200)


class ListingDeleteView(APIView):
    """Delete a listing (admin only).

    Deletion is blocked once any bid has been placed — the auction must be
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

        listing.delete()
        return Response(status=204)


class ListingCancelView(APIView):
    """Cancel an auction and notify all bidders (SFR-06c).

    Once cancelled the listing is locked: bidding stops and the admin may
    then modify or delete it.  Every unique bidder is emailed so they know
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
        _broadcast_catalogue_update()

        return Response(
            {
                "detail": "Auction cancelled.",
                "bidders_notified": notified,
            },
            status=200,
        )


@method_decorator(
    ratelimit(key="user_or_ip", rate="30/m", method="POST", block=True),
    name="post",
)
class BidSubmitView(BidImmutableMixin, APIView):
    """Submit a bid on an active auction (authenticated + verified)."""

    permission_classes = [IsEmailVerified]

    def post(self, request, listing_id):
        serializer = BidSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip = request.META.get("REMOTE_ADDR")
        ua = request.META.get("HTTP_USER_AGENT", "")
        amount_raw = serializer.validated_data["amount"]

        try:
            bid, listing = submit_bid(
                listing_id=listing_id,
                user=request.user,
                amount=amount_raw,
                ip_address=ip,
                user_agent=ua,
            )
        except OperationalError:
            # Row-level lock could not be acquired — concurrent bid in progress
            log_action(
                user=request.user,
                action="bid_rejected",
                resource_type="Listing",
                resource_id=listing_id,
                ip_address=ip,
                user_agent=ua,
                metadata={
                    "listing_id": str(listing_id),
                    "attempted_amount": str(amount_raw),
                    "reason": "lock_contention",
                    "user_role": "staff" if getattr(request.user, "is_staff", False) else "user",
                },
            )
            return Response(
                {"detail": "Another bid is being processed. Please try again."},
                status=409,
            )
        except LookupError:
            log_action(
                user=request.user,
                action="bid_rejected",
                resource_type="Listing",
                resource_id=listing_id,
                ip_address=ip,
                user_agent=ua,
                metadata={
                    "listing_id": str(listing_id),
                    "attempted_amount": str(amount_raw),
                    "reason": "listing_not_found",
                    "user_role": "staff" if getattr(request.user, "is_staff", False) else "user",
                },
            )
            return Response({"detail": "Listing not found."}, status=404)
        except PermissionDenied as exc:
            log_action(
                user=request.user,
                action="bid_forbidden",
                resource_type="Listing",
                resource_id=listing_id,
                ip_address=ip,
                user_agent=ua,
                metadata={
                    "listing_id": str(listing_id),
                    "attempted_amount": str(amount_raw),
                    "reason": str(exc),
                    "user_role": "staff" if getattr(request.user, "is_staff", False) else "user",
                    "security_event": True,
                },
            )
            return Response({"detail": str(exc)}, status=400)
        except ValueError as exc:
            log_action(
                user=request.user,
                action="bid_rejected",
                resource_type="Listing",
                resource_id=listing_id,
                ip_address=ip,
                user_agent=ua,
                metadata={
                    "listing_id": str(listing_id),
                    "attempted_amount": str(amount_raw),
                    "reason": str(exc),
                    "user_role": "staff" if getattr(request.user, "is_staff", False) else "user",
                },
            )
            return Response({"detail": str(exc)}, status=400)
        except Exception:
            # Fail-closed: any unhandled exception rolls back the transaction.
            # Log full detail server-side; return generic message to client (NFSR-AV-04).
            logger = logging.getLogger(__name__)
            logger.exception(
                "Unhandled exception during bid submission for listing %s by user %s",
                listing_id,
                getattr(request.user, "id", "unknown"),
            )
            log_action(
                user=request.user,
                action="bid_error",
                resource_type="Listing",
                resource_id=listing_id,
                ip_address=ip,
                user_agent=ua,
                metadata={
                    "listing_id": str(listing_id),
                    "attempted_amount": str(amount_raw),
                    "user_role": "staff" if getattr(request.user, "is_staff", False) else "user",
                    "security_event": True,
                },
            )
            return Response(
                {"detail": "An unexpected error occurred. Your bid was not placed."},
                status=500,
            )
        # bid_placed audit log is written inside the atomic block in submit_bid

        # Broadcast to all WebSocket viewers of this listing
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"auction_{listing.id}",
                {
                    "type": "bid.update",
                    "data": {
                        "event": "bid_placed",
                        "anonymous_identifier": bid.anonymous_identifier,
                        "amount": str(bid.amount),
                        "submitted_at": bid.submitted_at.isoformat(),
                        "is_winning": bid.is_winning,
                        "current_highest_bid": str(listing.current_highest_bid),
                        "bid_count": listing.bids.count(),
                    },
                },
            )

        return Response(
            {
                "detail": "Bid submitted.",
                "bid": BidSerializer(bid).data,
                "listing": {
                    "id": str(listing.id),
                    "current_highest_bid": listing.current_highest_bid,
                },
            },
            status=201,
        )


class ListingBidsView(BidImmutableMixin, APIView):
    """Return all bids for a listing, newest first. Public read."""

    permission_classes = [AllowAny]

    def get(self, request, listing_id):
        try:
            listing = Listing.objects.get(pk=listing_id)
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found."}, status=404)

        if not request.user.is_staff and listing.status in {"draft", "cancelled"}:
            return Response({"detail": "Listing not found."}, status=404)

        bids = (
            Bid.objects.filter(listing=listing)
            .order_by("-submitted_at", "-id")
            .values("id", "anonymous_identifier", "amount", "submitted_at", "is_winning")
        )
        return Response(list(bids))


class UserBidHistoryView(BidImmutableMixin, APIView):
    """List the authenticated user's own bid history."""

    permission_classes = [IsEmailVerifiedSilent]

    def get(self, request):
        from .models import Bid

        bids = Bid.objects.filter(bidder=request.user).order_by("-submitted_at")
        serializer = BidSerializer(bids, many=True)
        return Response(serializer.data)


class UserDashboardView(APIView):
    """Read dashboard data scoped to the authenticated user's UUID only."""

    permission_classes = [IsEmailVerifiedSilent]

    def get(self, request):
        from payments.models import Order

        if request.user.is_staff:
            return Response({"detail": "Admins cannot access the bidder dashboard."}, status=403)

        Listing.finalize_ended_auctions()

        now = timezone.now()
        user_id = request.user.id

        user_latest_bid_qs = Bid.objects.filter(
            listing=OuterRef("pk"),
            bidder_id=user_id,
        ).order_by("-submitted_at")
        winning_bidder_qs = Bid.objects.filter(
            listing=OuterRef("pk"),
            is_winning=True,
        ).order_by("-submitted_at")

        active_bid_listings = (
            Listing.objects.filter(
                bids__bidder_id=user_id,
                starts_at__lte=now,
                ends_at__gt=now,
            )
            .exclude(status__in=["draft", "cancelled"])
            .annotate(
                user_latest_bid_amount=Subquery(
                    user_latest_bid_qs.values("amount")[:1]
                ),
                user_latest_bid_submitted_at=Subquery(
                    user_latest_bid_qs.values("submitted_at")[:1]
                ),
                current_winning_bidder_id=Subquery(
                    winning_bidder_qs.values("bidder_id")[:1]
                ),
            )
            .order_by("ends_at")
            .distinct()
        )

        won_listings = (
            Listing.objects.filter(winner_id=user_id)
            .exclude(status__in=["draft", "cancelled"])
            .order_by("-ends_at")
        )

        history_listings = (
            Listing.objects.filter(bids__bidder_id=user_id)
            .exclude(status__in=["draft", "cancelled"])
            .annotate(
                user_latest_bid_amount=Subquery(
                    user_latest_bid_qs.values("amount")[:1]
                ),
                user_latest_bid_submitted_at=Subquery(
                    user_latest_bid_qs.values("submitted_at")[:1]
                ),
                user_bid_count=Count(
                    "bids",
                    filter=Q(bids__bidder_id=user_id),
                ),
            )
            .order_by("-ends_at", "-starts_at")
            .distinct()
        )

        orders = Order.objects.filter(winner_id=user_id).select_related(
            "winning_bid__listing"
        )
        orders_by_listing_id = {
            order.winning_bid.listing_id: order
            for order in orders
        }

        active_bids_data = [
            {
                "listing_id": listing.id,
                "title": listing.title,
                "image_key": listing.image_key,
                "ends_at": listing.ends_at,
                "current_highest_bid": listing.current_highest_bid,
                "user_latest_bid_amount": listing.user_latest_bid_amount,
                "user_latest_bid_submitted_at": listing.user_latest_bid_submitted_at,
                "is_currently_winning": (
                    listing.current_winning_bidder_id == user_id
                ),
            }
            for listing in active_bid_listings
        ]

        won_auctions_data = []
        for listing in won_listings:
            order = orders_by_listing_id.get(listing.id)
            won_auctions_data.append(
                {
                    "listing_id": listing.id,
                    "title": listing.title,
                    "image_key": listing.image_key,
                    "ended_at": listing.ends_at,
                    "winning_amount": listing.current_highest_bid,
                    "payment_status": (
                        order.fulfillment_status if order else "pending_payment"
                    ),
                    "order_id": order.id if order else None,
                }
            )

        payment_counts = {
            choice[0]: 0
            for choice in Order.FULFILLMENT_CHOICES
        }
        for order in orders:
            payment_counts[order.fulfillment_status] += 1

        payment_status_data = {
            "total_orders": len(orders_by_listing_id),
            "counts_by_status": payment_counts,
            "pending_payment_auctions": [
                item
                for item in won_auctions_data
                if item["payment_status"] == "pending_payment"
            ],
        }

        history_data = []
        for listing in history_listings:
            if listing.ends_at > now:
                result = "active"
            elif listing.winner_id == user_id:
                result = "won"
            elif listing.winner_id is None:
                result = "ended_no_winner"
            else:
                result = "lost"

            history_data.append(
                {
                    "listing_id": listing.id,
                    "title": listing.title,
                    "image_key": listing.image_key,
                    "starts_at": listing.starts_at,
                    "ends_at": listing.ends_at,
                    "status": listing.get_runtime_status(now=now),
                    "result": result,
                    "user_bid_count": listing.user_bid_count,
                    "user_latest_bid_amount": listing.user_latest_bid_amount,
                    "user_latest_bid_submitted_at": listing.user_latest_bid_submitted_at,
                    "final_price": listing.current_highest_bid,
                }
            )

        return Response(
            {
                "active_bids": active_bids_data,
                "won_auctions": won_auctions_data,
                "payment_status": payment_status_data,
                "auction_history": history_data,
            }
        )


class ListingImageUploadView(APIView):
    """Upload a listing image to a private Supabase Storage bucket (admin only)."""

    permission_classes = [IsAdminUser]
    staff_only = True
    parser_classes = [MultiPartParser]

    def post(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "No file provided."}, status=400)

        # upload_image validates size, real MIME type, and extension
        # server-side, and stores the file under a server-generated UUID
        # name (NFSR-IN-04 / NFSR-C-07 / NFSR-C-02). Any ValidationError it
        # raises is converted to a 400 by core.exceptions.custom_exception_handler.
        object_key = upload_image(f, f.name)
        return Response({"key": object_key}, status=201)
