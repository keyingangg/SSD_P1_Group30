"""Bid submission and read API (diagram: svc_bid)."""
import logging

from django.core.exceptions import PermissionDenied
from django.db import OperationalError
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.services.permissions import IsEmailVerified, IsEmailVerifiedSilent

from core.cross_cutting.audit import log_action, device_fingerprint as _device_fingerprint
from ..business.bid_engine import submit_bid
from ..data.models import Bid, Listing
from .serializers import BidSerializer, BidSubmitSerializer

_audit_logger = logging.getLogger(__name__)


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
            device_fingerprint=_device_fingerprint(request.META.get("REMOTE_ADDR"), request.META.get("HTTP_USER_AGENT", "")),
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


@method_decorator(
    ratelimit(key="user_or_ip", rate="30/m", method="POST", block=True),
    name="post",
)
class BidSubmitView(BidImmutableMixin, APIView):
    """Submit a bid on an active auction (authenticated + verified)."""

    permission_classes = [IsEmailVerified]
    # delete/patch are kept in the allowlist (not dropped) so BidImmutableMixin's
    # explicit reject-and-log handlers still run instead of a bare 405 (NFSR-AV-03).
    http_method_names = ["post", "delete", "patch"]

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
            # Row-level lock could not be acquired -- concurrent bid in progress
            log_action(
                user=request.user,
                action="bid_rejected",
                resource_type="Listing",
                resource_id=listing_id,
                ip_address=ip,
                user_agent=ua,
                device_fingerprint=_device_fingerprint(ip, ua),
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
                device_fingerprint=_device_fingerprint(ip, ua),
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
                device_fingerprint=_device_fingerprint(ip, ua),
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
                device_fingerprint=_device_fingerprint(ip, ua),
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
                device_fingerprint=_device_fingerprint(ip, ua),
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
        # WS broadcast is handled by _broadcast_bid inside submit_bid -- no extra sends needed.

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
    """Return all bids for a listing, newest first.

    Requires an authenticated, email-verified account -- bid activity (even
    pseudonymised via anonymous_identifier) is not public, matching the
    same gate BidConsumer already enforces over the WebSocket feed for
    this same data.
    """

    permission_classes = [IsEmailVerified]

    def get(self, request, listing_id):
        try:
            listing = Listing.objects.get(pk=listing_id)
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found."}, status=404)

        if not request.user.is_staff and listing.status in {"draft", "cancelled", "scheduled"}:
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
        bids = Bid.objects.filter(bidder=request.user).order_by("-submitted_at")
        serializer = BidSerializer(bids, many=True)
        return Response(serializer.data)
