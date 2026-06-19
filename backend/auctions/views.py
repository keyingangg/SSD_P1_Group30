"""API views for the auctions app."""
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser

from .models import Listing
from .serializers import ListingAdminSerializer, ListingCreateSerializer


class ListingListView(APIView):
    """Browse, search, and filter published listings (public)."""

    permission_classes = [AllowAny]

    def get(self, request):
        queryset = Listing.objects.all().order_by("-starts_at")
        if not request.user.is_staff:
            queryset = queryset.exclude(status__in=["draft", "ended", "cancelled"])
        serializer = ListingAdminSerializer(queryset, many=True)
        return Response(serializer.data)


class ListingDetailView(APIView):
    """View a single published listing's details (public)."""

    permission_classes = [AllowAny]

    def get(self, request, listing_id):
        try:
            listing = Listing.objects.get(pk=listing_id)
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found."}, status=404)

        if not request.user.is_staff and listing.status in {"draft", "ended", "cancelled"}:
            return Response({"detail": "Listing not found."}, status=404)

        serializer = ListingAdminSerializer(listing)
        return Response(serializer.data)


class ListingCreateView(APIView):
    """Create a new listing (admin only)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_staff:
            return Response({"detail": "Admin access required."}, status=403)

        serializer = ListingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        save_as_draft = data.get("save_as_draft", False)
        now = timezone.now()

        # Normalize image_key: store None when blank to keep DB consistent.
        img_key = data.get("image_key")
        if isinstance(img_key, str) and img_key.strip() == "":
            img_key = None

        starts_at = data.get("starts_at") or now
        ends_at = data.get("ends_at") or (starts_at + timedelta(days=1))
        minimum_increment = data.get("minimum_increment") or Decimal("1.00")

        listing = Listing.objects.create(
            created_by=request.user,
            title=data["title"],
            description=data.get("description", ""),
            image_key=img_key,
            category=data.get("category", "Others"),
            starting_price=data["starting_price"],
            minimum_increment=minimum_increment,
            starts_at=starts_at,
            ends_at=ends_at,
            status="draft" if save_as_draft else Listing.determine_status(starts_at, ends_at),
        )

        return Response({"detail": "Listing created.", "id": listing.id, "image_key": listing.image_key}, status=201)


class ListingUpdateView(APIView):
    """Update an existing listing (admin only)."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, listing_id):
        if not request.user.is_staff:
            return Response({"detail": "Admin access required."}, status=403)

        try:
            listing = Listing.objects.get(pk=listing_id)
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found."}, status=404)

        serializer = ListingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        listing.title = data["title"]
        listing.description = data["description"]
        listing.category = data.get("category", listing.category)
        listing.image_key = data.get("image_key", listing.image_key)
        listing.starting_price = data["starting_price"]
        listing.minimum_increment = data["minimum_increment"]
        listing.starts_at = data["starts_at"]
        listing.ends_at = data["ends_at"]
        if listing.status not in {"draft", "cancelled"}:
            listing.status = Listing.determine_status(listing.starts_at, listing.ends_at)
        listing.save()

        return Response({"detail": "Listing updated."}, status=200)


class ListingDeleteView(APIView):
    """Delete a listing (admin only)."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, listing_id):
        if not request.user.is_staff:
            return Response({"detail": "Admin access required."}, status=403)

        try:
            listing = Listing.objects.get(pk=listing_id)
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found."}, status=404)

        listing.delete()
        return Response(status=204)


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


class ListingImageUploadView(APIView):
    """Upload a listing image (authenticated, admin only)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if not request.user.is_staff:
            return Response({"detail": "Admin access required."}, status=403)

        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "No file provided."}, status=400)

        # Validate file size (5MB max) and content type
        if f.size > 5 * 1024 * 1024:
            return Response({"detail": "File too large (max 5MB)."}, status=400)
        if not f.content_type.startswith("image/"):
            return Response({"detail": "Invalid file type (must be image)."}, status=400)

        # Save with unique name
        name = f"listings/{uuid4().hex}_{f.name}"
        saved_name = default_storage.save(name, f)
        relative_url = default_storage.url(saved_name)

        return Response({"key": saved_name, "url": relative_url}, status=201)
