"""API views for the payments app."""
import logging

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminUser, IsEmailVerified
from core.audit import log_action
from . import stripe_client
from .models import Order

logger = logging.getLogger("securebid")


class CreatePaymentIntentView(APIView):
    """Create a payment intent for the authenticated auction winner."""

    permission_classes = [IsEmailVerified]

    def post(self, request):
        # DEMO MODE: Returns a mock Stripe client_secret for UI demonstration.
        # Replace with real stripe.PaymentIntent.create() call when going live.
        # TODO: verify caller is the order winner, bind checkout to their ID.
        mock = stripe_client.create_payment_intent(
            amount=0, currency="sgd", idempotency_key=None
        )
        return Response(mock, status=200)


class StripeWebhookView(APIView):
    """Receive Stripe webhook events (server-to-server)."""

    permission_classes = []  # Stripe is authenticated via signature, not session.

    def post(self, request):
        # TODO: verify HMAC-SHA256 signature before any DB write, then
        # reconcile payment intent against the winner record.
        return Response({"detail": "Not implemented."}, status=501)


class OrderDetailView(APIView):
    """Read a single order (scoped to the winner or an admin)."""

    permission_classes = [IsEmailVerified]

    def get(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id)
        if order.winner_id != request.user.id and not request.user.is_staff:
            logger.warning(
                "Order access denied for user=%s order=%s ip=%s agent=%s",
                request.user.email,
                order_id,
                request.META.get("REMOTE_ADDR", ""),
                request.META.get("HTTP_USER_AGENT", ""),
            )
            log_action(
                user=request.user,
                action="ORDER_ACCESS_DENIED",
                resource_type="Order",
                resource_id=order.id,
                ip_address=request.META.get("REMOTE_ADDR", ""),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                metadata={"requested_by": str(request.user.id)},
            )
            return Response({"detail": "Forbidden."}, status=403)

        return Response(
            {
                "id": str(order.id),
                "fulfillment_status": order.fulfillment_status,
                "delivery_address_snapshot": order.delivery_address_snapshot,
                "stripe_payment_intent_id": order.stripe_payment_intent_id,
            },
            status=200,
        )


class UpdateFulfillmentView(APIView):
    """Update an order's fulfilment status (admin only)."""

    permission_classes = [IsAdminUser]
    staff_only = True

    def patch(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id)
        status = request.data.get("fulfillment_status")
        if status not in dict(Order.FULFILLMENT_CHOICES):
            return Response({"detail": "Invalid fulfillment status."}, status=400)

        order.fulfillment_status = status
        order.save(update_fields=["fulfillment_status"])
        log_action(
            user=request.user,
            action="ORDER_FULFILLMENT_UPDATED",
            resource_type="Order",
            resource_id=order.id,
            ip_address=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            metadata={"fulfillment_status": status},
        )
        return Response({"detail": "Order fulfillment updated."}, status=200)
