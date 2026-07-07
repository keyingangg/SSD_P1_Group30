"""URL patterns for the auctions app."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.ListingListView.as_view(), name="listing-list"),
    path("admin/overview/", views.AdminOverviewView.as_view(), name="admin-overview"),
    path("create/", views.ListingCreateView.as_view(), name="listing-create"),
    path("upload-image/", views.ListingImageUploadView.as_view(), name="upload-image"),
    path(
        "dashboard/",
        views.UserDashboardView.as_view(),
        name="user-dashboard",
    ),
    path(
        "bids/history/",
        views.UserBidHistoryView.as_view(),
        name="bid-history",
    ),
    path(
        "<uuid:listing_id>/",
        views.ListingDetailView.as_view(),
        name="listing-detail",
    ),
    path(
        "<uuid:listing_id>/update/",
        views.ListingUpdateView.as_view(),
        name="listing-update",
    ),
    path(
        "<uuid:listing_id>/delete/",
        views.ListingDeleteView.as_view(),
        name="listing-delete",
    ),
    path(
        "<uuid:listing_id>/bid/",
        views.BidSubmitView.as_view(),
        name="bid-submit",
    ),
    path(
        "<uuid:listing_id>/bids/",
        views.ListingBidsView.as_view(),
        name="listing-bids",
    ),
    path(
        "<uuid:listing_id>/cancel/",
        views.ListingCancelView.as_view(),
        name="listing-cancel",
    ),
]
