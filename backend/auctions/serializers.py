"""Serializers for the auctions app."""
import logging

from rest_framework import serializers

from core.storage import get_signed_url
from .models import Bid, Listing

logger = logging.getLogger("securebid")


def _image_signed_url(image_key):
    """Convert a stored object key into a short-lived signed URL for clients.

    Images must only ever be served via signed URLs, never the raw object
    key or a public bucket URL (NFSR-C-07 / SFR-11e).
    """
    if not image_key:
        return None
    try:
        return get_signed_url(image_key)
    except Exception:
        logger.exception("Failed to generate signed URL for image_key=%s", image_key)
        return None


class ListingSerializer(serializers.ModelSerializer):
    """Serialize a listing for public/detail views (no bidder identities).

    image_key stays the raw stored object key (needed so admin edit forms
    can round-trip it unchanged when the image isn't being replaced);
    image_url is the short-lived signed URL clients should render.
    """

    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        return _image_signed_url(obj.image_key)

    status = serializers.SerializerMethodField()
    display_status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return obj.get_runtime_status()

    def get_display_status(self, obj):
        return obj.get_display_status()

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "description",
            "image_key",
            "image_url",
            "category",
            "starting_price",
            "minimum_increment",
            "starts_at",
            "ends_at",
            "status",
            "display_status",
            "current_highest_bid",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class BidSerializer(serializers.ModelSerializer):
    """Serialize a bid for display using only the anonymised identifier."""

    class Meta:
        model = Bid
        fields = [
            "id",
            "anonymous_identifier",
            "amount",
            "submitted_at",
            "is_winning",
        ]
        read_only_fields = fields


class BidSubmitSerializer(serializers.Serializer):
    """Validate an incoming bid submission (amount only)."""

    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Bid amount must be greater than zero.")
        return value


class ListingCreateSerializer(serializers.Serializer):
    """Validate admin listing creation input."""

    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    image_key = serializers.CharField(max_length=512, required=False, allow_blank=True)
    category = serializers.CharField(max_length=50, required=False, default="Others")
    starting_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    minimum_increment = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    starts_at = serializers.DateTimeField(required=False)
    ends_at = serializers.DateTimeField(required=False)
    save_as_draft = serializers.BooleanField(required=False, default=False)

    def validate(self, data):
        save_as_draft = data.get("save_as_draft", False)

        if save_as_draft:
            return data

        required_fields = ["description", "minimum_increment", "starts_at", "ends_at"]
        missing = [field for field in required_fields if field not in data]
        if missing:
            raise serializers.ValidationError(
                {field: "This field is required." for field in missing}
            )

        if data["ends_at"] <= data["starts_at"]:
            raise serializers.ValidationError(
                {"ends_at": "Auction end time must be after the start time."}
            )
        return data


class ListingAdminSerializer(serializers.ModelSerializer):
    """image_key is the raw stored key (for round-tripping into edit forms);
    image_url is the short-lived signed URL for display."""

    status = serializers.SerializerMethodField()
    display_status = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    def get_status(self, obj):
        return obj.get_runtime_status()

    def get_display_status(self, obj):
        return obj.get_display_status()

    def get_image_url(self, obj):
        return _image_signed_url(obj.image_key)

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "description",
            "image_key",
            "image_url",
            "category",
            "starting_price",
            "minimum_increment",
            "starts_at",
            "ends_at",
            "status",
            "display_status",
            "current_highest_bid",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "current_highest_bid",
            "created_at",
            "updated_at",
            "status",
            "display_status",
        ]
