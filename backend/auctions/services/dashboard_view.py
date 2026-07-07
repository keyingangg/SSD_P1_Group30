"""User bidder dashboard API (diagram: svc_dashboard)."""
from django.db.models import Count, OuterRef, Q, Subquery
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.services.permissions import IsEmailVerifiedSilent

from ..business.listing_service import finalize_ended_auctions
from ..data.models import Bid, Listing


class UserDashboardView(APIView):
    """Read dashboard data scoped to the authenticated user's UUID only."""

    permission_classes = [IsEmailVerifiedSilent]

    def get(self, request):
        from payments.models import Order

        if request.user.is_staff:
            return Response({"detail": "Admins cannot access the bidder dashboard."}, status=403)

        finalize_ended_auctions()

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
