"""Serializers for the auctions app."""
from rest_framework import serializers

from .models import Listing


class ListingSerializer(serializers.Serializer):
    """Serialize a listing for public/detail views (no bidder identities)."""

    # TODO: expose safe listing fields, anonymised highest bid.
    pass


class BidSerializer(serializers.Serializer):
    """Serialize a bid for display using only the anonymised identifier."""

    # TODO: expose anonymous_identifier, amount, submitted_at.
    pass


class BidSubmitSerializer(serializers.Serializer):
    """Validate an incoming bid submission (amount only)."""

    # TODO: define amount field; all validation re-checked server-side.
    pass


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
