"""Public listing browse/detail API (diagram: svc_listing_browse)."""
from django.db.models import Count
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.services.permissions import IsEmailVerified

from core.cross_cutting.audit import log_action, device_fingerprint as _device_fingerprint
from ..data.models import Listing
from .serializers import ListingSearchQuerySerializer, ListingSerializer


def _unauth_ip_key(group, request):
    """Rate-limit key: the client's IP address.

    Always returns a string -- django-ratelimit's key callable does not
    support returning None to skip the check (it crashes on non-string
    values). Skipping for authenticated users is done via `_unauth_only_rate`
    instead, which is the mechanism the library actually supports.
    """
    return request.META.get("REMOTE_ADDR", "")


def _unauth_only_rate(group, request):
    """Rate for unauthenticated requests only.

    Returns None for authenticated users so django-ratelimit skips the check
    entirely -- authenticated users are already throttled on write actions.
    """
    if getattr(request.user, "is_authenticated", False):
        return None
    return "30/m"


@method_decorator(
    ratelimit(key=_unauth_ip_key, rate=_unauth_only_rate, method="GET", block=True),
    name="get",
)
class ListingListView(APIView):
    """Browse, search, and filter published listings (public)."""

    permission_classes = [AllowAny]

    def get(self, request):
        query = ListingSearchQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data

        now = timezone.now()
        Listing.finalize_ended_auctions(now=now)
        Listing.objects.filter(
            status="scheduled", starts_at__lte=now, ends_at__gt=now
        ).update(status="active")
        queryset = Listing.objects.annotate(_bid_count=Count("bids"))
        if not request.user.is_staff:
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
        queryset = queryset.order_by(params.get("ordering", "-starts_at"))

        serializer = ListingSerializer(queryset, many=True)
        return Response(serializer.data)


@method_decorator(
    ratelimit(key=_unauth_ip_key, rate=_unauth_only_rate, method="GET", block=True),
    name="get",
)
class ListingDetailView(APIView):
    """View a single published listing's details.

    Requires an authenticated, email-verified account -- the response
    includes bidding details (current_highest_bid, bid_count, minimum
    increment), which are gated the same way as the bid list itself
    (see ListingBidsView).
    """

    permission_classes = [IsEmailVerified]

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

        if not request.user.is_staff and listing.status in {"draft", "cancelled", "scheduled"}:
            log_action(
                user=request.user if getattr(request.user, "is_authenticated", False) else None,
                action="listing_access_denied",
                resource_type="Listing",
                resource_id=listing.id,
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                device_fingerprint=_device_fingerprint(request.META.get("REMOTE_ADDR"), request.META.get("HTTP_USER_AGENT", "")),
                request_method=request.method,
                endpoint_path=request.path,
                metadata={"reason": "listing_not_public", "listing_status": listing.status},
            )
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
