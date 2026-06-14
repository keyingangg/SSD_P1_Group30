"""API views for the payments app."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import stripe_client


class CreatePaymentIntentView(APIView):
    """Create a payment intent for the authenticated auction winner."""

    permission_classes = [IsAuthenticated]

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

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        # TODO: return order if request.user is the winner or an admin.
        return Response({"detail": "Not implemented."}, status=501)


class UpdateFulfillmentView(APIView):
    """Update an order's fulfilment status (admin only)."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, order_id):
        # TODO: admin check, update fulfilment_status, audit log.
        return Response({"detail": "Not implemented."}, status=501)
