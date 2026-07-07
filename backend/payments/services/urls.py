"""URL patterns for the payments app."""
from django.urls import path

from . import views

urlpatterns = [
    path(
        "create-intent/",
        views.CreatePaymentIntentView.as_view(),
        name="create-payment-intent",
    ),
    path("webhook/", views.StripeWebhookView.as_view(), name="stripe-webhook"),
    path("orders/", views.AdminOrderListView.as_view(), name="admin-order-list"),
    path(
        "orders/<uuid:order_id>/",
        views.OrderDetailView.as_view(),
        name="order-detail",
    ),
    path(
        "orders/<uuid:order_id>/confirm/",
        views.ConfirmPaymentView.as_view(),
        name="confirm-payment",
    ),
    path(
        "orders/<uuid:order_id>/fulfillment/",
        views.UpdateFulfillmentView.as_view(),
        name="update-fulfillment",
    ),
]
