"""API views for the auctions app."""
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class ListingListView(APIView):
    """Browse, search, and filter published listings (public)."""

    permission_classes = [AllowAny]

    def get(self, request):
        # TODO: return published listings only; support search/filter.
        return Response({"detail": "Not implemented."}, status=501)


class ListingDetailView(APIView):
    """View a single published listing's details (public)."""

    permission_classes = [AllowAny]

    def get(self, request, listing_id):
        # TODO: return listing; 404 for draft/scheduled to non-admins.
        return Response({"detail": "Not implemented."}, status=501)


class ListingCreateView(APIView):
    """Create a new listing (admin only)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # TODO: admin check, validate + sanitise input, create listing.
        return Response({"detail": "Not implemented."}, status=501)


class ListingUpdateView(APIView):
    """Update an existing listing (admin only)."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, listing_id):
        # TODO: admin check, block edits after bids unless cancelled.
        return Response({"detail": "Not implemented."}, status=501)


class ListingDeleteView(APIView):
    """Delete a listing (admin only)."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, listing_id):
        # TODO: admin check, delete/cancel listing.
        return Response({"detail": "Not implemented."}, status=501)


class BidSubmitView(APIView):
    """Submit a bid on an active auction (authenticated + verified)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, listing_id):
        # TODO: delegate to bid_engine.submit_bid with full validation.
        return Response({"detail": "Not implemented."}, status=501)


class UserBidHistoryView(APIView):
    """List the authenticated user's own bid history."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # TODO: return bids scoped to request.user.
        return Response({"detail": "Not implemented."}, status=501)
