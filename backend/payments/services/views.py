"""Aggregates the Services Layer API view modules so payments.services.urls
sees one payments.services.views namespace, while each API (diagram box)
lives in its own file."""
from .payment_intent_view import CreatePaymentIntentView  # noqa: F401
from .stripe_webhook_view import StripeWebhookView  # noqa: F401
from .admin_order_list_view import AdminOrderListView  # noqa: F401
from .order_detail_view import OrderDetailView  # noqa: F401
from .confirm_payment_view import ConfirmPaymentView  # noqa: F401
from .update_fulfillment_view import UpdateFulfillmentView  # noqa: F401
