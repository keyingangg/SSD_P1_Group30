"""Serializers for the auctions app."""
import html
import logging
from decimal import Decimal

from rest_framework import serializers

from core.cross_cutting.storage import get_signed_url
from ..data.models import Bid, Listing

logger = logging.getLogger("securebid")

# Allowlist of valid category values (NFSR-IN-03).
_VALID_CATEGORIES = [choice[0] for choice in Listing.CATEGORY_CHOICES]


def _image_signed_url(image_key):
    if not image_key:
        return None
    try:
        return get_signed_url(image_key)
    except Exception:
        logger.exception("Failed to generate signed URL for image_key=%s", image_key)
        return None


def _encode_text(value):
    """HTML-encode a string to neutralise stored XSS (SFR-06a / AR-08).

    Applied to all admin-submitted free-text fields before they leave the
    API boundary.  html.escape converts < > & " ' to their named entities so
    that even if the client renders the value in an unsafe HTML context the
    payload cannot execute.
    """
    if not isinstance(value, str):
        return value
    return html.escape(value, quote=True)


class ListingSerializer(serializers.ModelSerializer):
    """Serialize a listing for public/detail views (no bidder identities).

    image_key stays the raw stored object key (needed so admin edit forms
    can round-trip it unchanged when the image isn't being replaced);
    image_url is the short-lived signed URL clients should render.
    """

    image_url = serializers.SerializerMethodField()
    display_status = serializers.SerializerMethodField()
    bid_count = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        return _image_signed_url(obj.image_key)

    def get_display_status(self, obj):
        return obj.get_display_status()

    def get_bid_count(self, obj):
        # Use the pre-annotated value from the list queryset to avoid N+1 queries
        if hasattr(obj, "_bid_count"):
            return obj._bid_count
        return obj.bids.count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Output-encode all admin-supplied free-text fields (SFR-06a / AR-08).
        data["title"] = _encode_text(data.get("title", ""))
        data["description"] = _encode_text(data.get("description", ""))
        return data

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
            "bid_count",
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
    """Validate an incoming bid submission.

    Enforces type (Decimal), sign (> 0), and range (≤ 12 digits, 2 d.p.)
    constraints per NFSR-IN-03.
    """

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=Decimal("9999999999.99"),
    )

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Bid amount must be greater than zero.")
        return value


_ORDERING_CHOICES = [
    "starts_at", "-starts_at",
    "current_highest_bid", "-current_highest_bid",
    "ends_at", "-ends_at",
]


class ListingSearchQuerySerializer(serializers.Serializer):
    """Validate listing search/filter query params (SFR-11d).

    All fields optional; ordering is restricted to an explicit allowlist
    rather than accepting a raw field name (NFSR-IN-03).
    """

    q = serializers.CharField(max_length=255, required=False, allow_blank=True)
    category = serializers.ChoiceField(choices=_VALID_CATEGORIES, required=False)
    status = serializers.ChoiceField(
        choices=[choice[0] for choice in Listing.STATUS_CHOICES], required=False
    )
    min_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False
    )
    max_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False
    )
    ordering = serializers.ChoiceField(choices=_ORDERING_CHOICES, required=False)


class ListingCreateSerializer(serializers.Serializer):
    """Validate admin listing creation and update input.

    All constraints follow NFSR-IN-03 (type, length, range, sign) with an
    allowlist for the category field (FSR-IN-05).
    """

    title = serializers.CharField(
        min_length=1,
        max_length=255,
        trim_whitespace=True,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=10_000,
    )
    image_key = serializers.CharField(
        max_length=512,
        required=False,
        allow_blank=True,
    )
    # Allowlist: only values defined in Listing.CATEGORY_CHOICES are accepted.
    category = serializers.ChoiceField(
        choices=_VALID_CATEGORIES,
        required=False,
        default="Others",
    )
    starting_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=Decimal("9999999999.99"),
        required=False,
        allow_null=True,
    )
    minimum_increment = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=Decimal("9999999999.99"),
        required=False,
    )
    starts_at = serializers.DateTimeField(required=False, allow_null=True)
    ends_at = serializers.DateTimeField(required=False, allow_null=True)
    save_as_draft = serializers.BooleanField(required=False, default=False)

    def validate_title(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Title must not be blank.")
        return stripped

    def validate_starting_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Starting price must be greater than zero.")
        return value

    def validate_minimum_increment(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Minimum increment must be greater than zero.")
        return value

    def validate(self, data):
        save_as_draft = data.get("save_as_draft", False)

        if save_as_draft:
            return data

        required_fields = ["starting_price", "description", "minimum_increment", "starts_at", "ends_at"]
        missing = [field for field in required_fields if field not in data or data[field] is None]
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
    """Admin view of a listing — output-encodes free-text fields (SFR-06a / AR-08).

    image_key is the raw stored key (for round-tripping into edit forms);
    image_url is the short-lived signed URL for display.
    """

    status = serializers.SerializerMethodField()
    display_status = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    def get_status(self, obj):
        return obj.get_runtime_status()

    def get_display_status(self, obj):
        return obj.get_display_status()

    def get_image_url(self, obj):
        return _image_signed_url(obj.image_key)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["title"] = _encode_text(data.get("title", ""))
        data["description"] = _encode_text(data.get("description", ""))
        return data

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
