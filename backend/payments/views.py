"""API views for the payments app."""
import json
import logging
from decimal import Decimal

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminUser, IsEmailVerified
from core.audit import log_action
from core.storage import get_signed_url
from . import stripe_client
from .models import Order
from .serializers import CreatePaymentIntentSerializer, UpdateFulfillmentSerializer

logger = logging.getLogger("securebid")


def _amount_to_cents(amount):
    """Convert a Decimal dollar amount to an integer minor-unit (cents) value."""
    return int((Decimal(amount) * 100).quantize(Decimal("1")))


# Forward-only fulfilment progression (server-enforced, FR-10). An order may
# only advance to the single next state — never skip ahead or move backwards.
# pending_payment -> paid is driven by the Stripe webhook, not this endpoint.
FULFILLMENT_TRANSITIONS = {
    "paid": "processing",
    "processing": "shipped",
    "shipped": "delivered",
}


class CreatePaymentIntentView(APIView):
    """Create a Stripe PaymentIntent for the authenticated auction winner."""

    permission_classes = [IsEmailVerified]

    def post(self, request):
        serializer = CreatePaymentIntentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order_id = serializer.validated_data["order_id"]
        delivery_address = serializer.validated_data.get("delivery_address", "")

        order = get_object_or_404(Order, pk=order_id)

        # IDOR protection: only the winner may pay for their own order.
        if order.winner_id != request.user.id:
            logger.warning(
                "Checkout access denied for user=%s order=%s ip=%s",
                request.user.email,
                order_id,
                request.META.get("REMOTE_ADDR", ""),
            )
            log_action(
                user=request.user,
                action="CHECKOUT_ACCESS_DENIED",
                resource_type="Order",
                resource_id=order.id,
                ip_address=request.META.get("REMOTE_ADDR", ""),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                metadata={"requested_by": str(request.user.id), "security_event": True},
            )
            return Response({"detail": "Forbidden."}, status=403)

        if order.fulfillment_status != "pending_payment":
            return Response(
                {"detail": "This order has already been paid."},
                status=400,
            )

        # Auto-heal: if a prior PaymentIntent exists, check whether Stripe
        # already confirmed it (handles DB/webhook desync from a failed confirm).
        if order.stripe_payment_intent_id:
            try:
                prior = stripe_client.retrieve_payment_intent(order.stripe_payment_intent_id)
                if prior.get("status") == "succeeded":
                    order.fulfillment_status = "paid"
                    order.save(update_fields=["fulfillment_status", "updated_at"])
                    log_action(
                        user=request.user,
                        action="ORDER_PAID",
                        resource_type="Order",
                        resource_id=order.id,
                        metadata={"payment_intent": order.stripe_payment_intent_id, "source": "auto_heal"},
                    )
                    logger.info("Order %s auto-healed to paid (pi=%s)", order.id, order.stripe_payment_intent_id)
                    return Response({"detail": "This order has already been paid."}, status=400)
            except Exception:
                pass  # Can't retrieve — proceed normally

        # Persist the delivery address snapshot if the winner supplied one.
        if delivery_address:
            order.delivery_address_snapshot = delivery_address
            order.save(update_fields=["delivery_address_snapshot", "updated_at"])

        # Prefer the persisted amount (source of truth); fall back to the bid
        # for any legacy row not yet backfilled.
        amount_cents = _amount_to_cents(order.amount or order.winning_bid.amount)

        intent = stripe_client.create_payment_intent(
            amount_cents=amount_cents,
            currency=settings.STRIPE_CURRENCY,
            idempotency_key=order.stripe_idempotency_key,
            metadata={
                "order_id": str(order.id),
                "winner_id": str(order.winner_id),
            },
        )

        # Capture the request context onto the payment record for the audit
        # trail (FSR-AC-10). session_key may be None under token auth — store "".
        order.ip_address = request.META.get("REMOTE_ADDR", "") or None
        order.session_id = request.session.session_key or ""

        # Record the PaymentIntent id so the webhook can reconcile it later.
        update_fields = ["ip_address", "session_id", "updated_at"]
        if intent.get("id"):
            order.stripe_payment_intent_id = intent["id"]
            update_fields.append("stripe_payment_intent_id")
        order.save(update_fields=update_fields)

        log_action(
            user=request.user,
            action="CHECKOUT_INITIATED",
            resource_type="Order",
            resource_id=order.id,
            ip_address=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            request_method=request.method,
            endpoint_path=request.path,
            metadata={
                "order_id": str(order.id),
                "amount_cents": amount_cents,
                "currency": settings.STRIPE_CURRENCY,
            },
        )

        return Response(
            {
                "client_secret": intent["client_secret"],
                "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
                "amount": amount_cents,
                "currency": intent["currency"],
                "demo": intent.get("demo", False),
            },
            status=200,
        )


class StripeWebhookView(APIView):
    """Receive Stripe webhook events (server-to-server)."""

    # Stripe authenticates via the request signature, not a session — disable
    # session auth/CSRF and allow the unauthenticated server-to-server call.
    authentication_classes = []
    permission_classes = [AllowAny]

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
            self._handle_payment_succeeded(obj)
        elif event_type == "payment_intent.payment_failed":
            logger.info(
                "Stripe webhook: payment failed for intent=%s", obj.get("id")
            )

        # Always 200 so Stripe stops retrying once we've safely received it.
        return Response({"received": True}, status=200)

    def _handle_payment_succeeded(self, intent):
        payment_intent_id = intent.get("id")
        metadata = intent.get("metadata") or {}
        claimed_winner_id = metadata.get("winner_id")

        order = Order.objects.filter(
            stripe_payment_intent_id=payment_intent_id
        ).first()
        if order is None:
            logger.warning(
                "Stripe webhook: no order for payment_intent=%s", payment_intent_id
            )
            return

        # Cross-reference the winner: the metadata winner must match the order's
        # recorded winner. A mismatch halts processing and raises a logged alert.
        if claimed_winner_id and str(order.winner_id) != str(claimed_winner_id):
            logger.error(
                "Stripe webhook MISMATCH: order=%s order_winner=%s "
                "metadata_winner=%s intent=%s — halting, not marking paid",
                order.id,
                order.winner_id,
                claimed_winner_id,
                payment_intent_id,
            )
            log_action(
                user=None,
                action="PAYMENT_WINNER_MISMATCH",
                resource_type="Order",
                resource_id=order.id,
                metadata={
                    "order_winner": str(order.winner_id),
                    "claimed_winner": str(claimed_winner_id),
                    "payment_intent": str(payment_intent_id),
                    "security_event": True,
                },
            )
            return

        if order.fulfillment_status == "pending_payment":
            order.fulfillment_status = "paid"
            order.save(update_fields=["fulfillment_status", "updated_at"])
            log_action(
                user=order.winner,
                action="ORDER_PAID",
                resource_type="Order",
                resource_id=order.id,
                metadata={"payment_intent": str(payment_intent_id)},
            )
            logger.info("Order %s marked paid via webhook", order.id)


def _mask_winner(winner):
    """Return a privacy-masked display name for the winner (first + *** + last char)."""
    name = getattr(winner, "display_name", "") or ""
    if not name:
        name = winner.email.split("@")[0]
    name = name.strip()
    if len(name) <= 2:
        return name[0] + "***"
    return name[0] + "***" + name[-1]


class AdminOrderListView(APIView):
    """List all orders for admin review — admin/staff only (FR-10, FR-11)."""

    permission_classes = [IsAdminUser]
    staff_only = True

    def get(self, request):
        orders = (
            Order.objects.select_related(
                "winner", "winning_bid", "winning_bid__listing"
            )
            .order_by("-created_at")
        )

        results = []
        for order in orders:
            listing = order.winning_bid.listing
            winner = order.winner

            image_url = None
            if listing.image_key:
                try:
                    image_url = get_signed_url(listing.image_key)
                except Exception:
                    pass

            results.append(
                {
                    "id": str(order.id),
                    "order_ref": f"SB-{str(order.id).upper()[:8]}",
                    "fulfillment_status": order.fulfillment_status,
                    "amount": _amount_to_cents(order.amount or order.winning_bid.amount),
                    "currency": order.currency or settings.STRIPE_CURRENCY,
                    "listing_title": listing.title,
                    "listing_image_url": image_url,
                    "winner_display": _mask_winner(winner),
                    "winner_is_verified": getattr(winner, "is_email_verified", False),
                    "has_delivery_address": bool(order.delivery_address_snapshot),
                    "created_at": order.created_at.isoformat(),
                    "updated_at": order.updated_at.isoformat(),
                }
            )

        return Response(results, status=200)


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

        listing = order.winning_bid.listing
        image_url = None
        if listing.image_key:
            try:
                image_url = get_signed_url(listing.image_key)
            except Exception:
                image_url = None

        won_at = None
        if listing.ends_at:
            try:
                won_at = listing.ends_at.isoformat()
            except Exception:
                pass

        return Response(
            {
                "id": str(order.id),
                "order_ref": f"SB-{str(order.id).upper()[:8]}",
                "fulfillment_status": order.fulfillment_status,
                "delivery_address_snapshot": order.delivery_address_snapshot,
                "amount": _amount_to_cents(order.amount or order.winning_bid.amount),
                "currency": order.currency or settings.STRIPE_CURRENCY,
                "listing_title": listing.title,
                "listing_image_url": image_url,
                "won_at": won_at,
            },
            status=200,
        )


class ConfirmPaymentView(APIView):
    """Directly confirm payment by verifying the PaymentIntent with Stripe's API.

    Called by the frontend immediately after stripe.confirmPayment() succeeds.
    Eliminates the need for the Stripe CLI / webhook listener in development.
    The webhook remains as a safety net for edge cases (browser crash, etc.).
    """

    permission_classes = [IsEmailVerified]

    def post(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id)

        if order.winner_id != request.user.id:
            logger.warning(
                "ConfirmPayment access denied user=%s order=%s ip=%s",
                request.user.email, order_id, request.META.get("REMOTE_ADDR", ""),
            )
            return Response({"detail": "Forbidden."}, status=403)

        # Idempotent — already confirmed by webhook or a prior call.
        if order.fulfillment_status != "pending_payment":
            return Response({"detail": "Payment already confirmed."}, status=200)

        payment_intent_id = request.data.get("payment_intent_id", "").strip()
        if not payment_intent_id:
            return Response({"detail": "payment_intent_id is required."}, status=400)

        # Retrieve and verify directly with Stripe — never trust the client's claim.
        try:
            intent = stripe_client.retrieve_payment_intent(payment_intent_id)
        except Exception as exc:
            logger.warning(
                "ConfirmPayment: retrieve failed pi=%s error=%s", payment_intent_id, exc
            )
            return Response({"detail": "Could not verify payment with Stripe."}, status=400)

        if not intent.get("demo"):
            if intent.get("status") != "succeeded":
                return Response({"detail": "Payment has not completed."}, status=400)

            # Cross-check metadata to ensure this PI was created for this order.
            metadata = intent.get("metadata", {})
            if str(metadata.get("order_id", "")) != str(order.id):
                logger.error(
                    "ConfirmPayment mismatch: pi=%s pi_order=%s req_order=%s user=%s",
                    payment_intent_id, metadata.get("order_id"), order.id, request.user.email,
                )
                log_action(
                    user=request.user,
                    action="PAYMENT_CONFIRM_MISMATCH",
                    resource_type="Order",
                    resource_id=order.id,
                    ip_address=request.META.get("REMOTE_ADDR", ""),
                    metadata={"payment_intent": payment_intent_id, "security_event": True},
                )
                return Response({"detail": "Payment does not match this order."}, status=400)

        order.fulfillment_status = "paid"
        if not intent.get("demo"):
            order.stripe_payment_intent_id = payment_intent_id
        order.save(update_fields=["fulfillment_status", "stripe_payment_intent_id", "updated_at"])

        log_action(
            user=request.user,
            action="ORDER_PAID",
            resource_type="Order",
            resource_id=order.id,
            ip_address=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            metadata={"payment_intent": payment_intent_id, "source": "direct_confirm"},
        )
        logger.info("Order %s paid via direct confirm (pi=%s)", order.id, payment_intent_id)
        return Response({"detail": "Payment confirmed."}, status=200)


class UpdateFulfillmentView(APIView):
    """Update an order's fulfilment status (admin only), forward-only."""

    permission_classes = [IsAdminUser]
    staff_only = True

    def patch(self, request, order_id):
        serializer = UpdateFulfillmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["fulfillment_status"]

        order = get_object_or_404(Order, pk=order_id)

        if new_status not in dict(Order.FULFILLMENT_CHOICES):
            return Response({"detail": "Invalid fulfillment status."}, status=400)

        # Enforce forward-only progression: the new status must be exactly the
        # single allowed next state for the order's current status.
        allowed_next = FULFILLMENT_TRANSITIONS.get(order.fulfillment_status)
        if new_status != allowed_next:
            return Response(
                {
                    "detail": (
                        f"Cannot move order from '{order.fulfillment_status}' to "
                        f"'{new_status}'. "
                        + (
                            f"The next allowed status is '{allowed_next}'."
                            if allowed_next
                            else "This order can no longer be advanced."
                        )
                    )
                },
                status=400,
            )

        order.fulfillment_status = new_status
        order.save(update_fields=["fulfillment_status", "updated_at"])
        log_action(
            user=request.user,
            action="ORDER_FULFILLMENT_UPDATED",
            resource_type="Order",
            resource_id=order.id,
            ip_address=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            metadata={"fulfillment_status": new_status},
        )
        return Response({"detail": "Order fulfillment updated."}, status=200)
