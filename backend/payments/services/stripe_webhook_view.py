"""Stripe webhook receiver API (diagram: svc_stripe_webhook)."""
import json
import logging

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..business import stripe_client
from ..business.order_service import OrderService

logger = logging.getLogger("securebid")


class StripeWebhookView(APIView):
    """Receive Stripe webhook events (server-to-server)."""

    # Stripe authenticates via the request signature, not a session — disable
    # session auth/CSRF and allow the unauthenticated server-to-server call.
    authentication_classes = []
    permission_classes = [AllowAny]
    http_method_names = ["post"]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        # Verify the HMAC-SHA256 signature BEFORE any DB write (FR-10).
        try:
            stripe_client.construct_webhook_event(payload, sig_header)
        except ValueError:
            logger.warning("Stripe webhook: invalid payload")
            return Response({"detail": "Invalid payload."}, status=400)
        except Exception:
            # stripe.error.SignatureVerificationError and any other failure.
            logger.warning("Stripe webhook: signature verification failed")
            return Response({"detail": "Invalid signature."}, status=400)

        # Parse the raw JSON for plain dict access — avoids Stripe SDK object quirks.
        event = json.loads(payload)
        event_type = event.get("type")
        obj = event.get("data", {}).get("object", {})

        if event_type == "payment_intent.succeeded":
            OrderService.handle_payment_succeeded(obj, ip_address=request.META.get("REMOTE_ADDR"))
        elif event_type == "payment_intent.payment_failed":
            logger.info(
                "Stripe webhook: payment failed for intent=%s", obj.get("id")
            )

        # Always 200 so Stripe stops retrying once we've safely received it.
        return Response({"received": True}, status=200)
