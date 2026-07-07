"""Aggregates the Services Layer API view modules so auctions.services.urls
sees one auctions.services.views namespace, while each API (diagram box)
lives in its own file."""
from .listing_browse_view import ListingDetailView, ListingListView  # noqa: F401
from .listing_admin_view import (  # noqa: F401
    ListingCancelView,
    ListingCreateView,
    ListingDeleteView,
    ListingUpdateView,
)
from .bid_view import (  # noqa: F401
    BidImmutableMixin,
    BidSubmitView,
    ListingBidsView,
    UserBidHistoryView,
)
from .dashboard_view import UserDashboardView  # noqa: F401
from .listing_image_view import ListingImageUploadView  # noqa: F401
from .admin_overview_view import AdminOverviewView  # noqa: F401
