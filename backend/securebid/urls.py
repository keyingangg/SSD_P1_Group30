"""Root URL configuration for the SecureBid project."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("sb-manage/", admin.site.urls),
    path("api/accounts/", include("accounts.services.urls")),
    path("api/auctions/", include("auctions.services.urls")),
    path("api/payments/", include("payments.services.urls")),
]

# Serve media files in development.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
