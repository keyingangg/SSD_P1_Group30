"""Root URL configuration for the SecureBid project."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/accounts/", include("accounts.urls")),
    path("api/auctions/", include("auctions.urls")),
    path("api/payments/", include("payments.urls")),
]
