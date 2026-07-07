"""Business logic for order retrieval, checkout, and payment confirmation."""
import logging
from decimal import Decimal

from django.conf import settings

from core.cross_cutting.audit import log_action
from core.cross_cutting.storage import get_signed_url

from ..data.models import Order
from . import stripe_client

logger = logging.getLogger("securebid")


class OrderAccessDenied(Exception):
    """Raised when a user attempts to access an order they don't own."""


class OrderServiceError(Exception):
    """Raised for order/payment business-rule violations; carries an HTTP status."""

    def __init__(self, detail, status_code=400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class OrderService:
    """Order presentation, checkout, and payment-confirmation logic."""

    @staticmethod
    def amount_to_cents(amount):
        """Convert a Decimal dollar amount to an integer minor-unit (cents) value."""
        return int((Decimal(amount) * 100).quantize(Decimal("1")))

    @staticmethod
    def mask_winner(winner):
        """Return a privacy-masked display name for the winner (first + *** + last char)."""
        name = getattr(winner, "display_name", "") or ""
        if not name:
            name = winner.email.split("@")[0]
        name = name.strip()
        if len(name) <= 2:
            return name[0] + "***"
        return name[0] + "***" + name[-1]

    @staticmethod
    def assert_can_access_order(order, user):
        """Raise OrderAccessDenied unless the user is the winner or staff."""
        if order.winner_id != user.id and not user.is_staff:
            raise OrderAccessDenied()

    @classmethod
    def list_for_admin(cls):
        """Build the admin order-list rows (FR-10, FR-11)."""
        orders = (
            Order.objects.select_related("winner", "winning_bid", "winning_bid__listing")
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
                    "amount": cls.amount_to_cents(order.amount or order.winning_bid.amount),
                    "currency": order.currency or settings.STRIPE_CURRENCY,
                    "listing_title": listing.title,
                    "listing_image_url": image_url,
                    "winner_display": cls.mask_winner(winner),
                    "winner_is_verified": getattr(winner, "is_email_verified", False),
                    "has_delivery_address": bool(order.delivery_address_snapshot),
                    "created_at": order.created_at.isoformat(),
                    "updated_at": order.updated_at.isoformat(),
                }
            )
        return results

    @classmethod
    def get_detail(cls, order):
        """Build the single-order detail payload (scoped to winner or admin by the caller)."""
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
        return {
            "id": str(order.id),
            "order_ref": f"SB-{str(order.id).upper()[:8]}",
            "fulfillment_status": order.fulfillment_status,
            "delivery_address_snapshot": order.delivery_address_snapshot,
            "amount": cls.amount_to_cents(order.amount or order.winning_bid.amount),
            "currency": order.currency or settings.STRIPE_CURRENCY,
            "listing_title": listing.title,
            "listing_image_url": image_url,
            "won_at": won_at,
        }

    @classmethod
    def initiate_checkout(cls, order, user, delivery_address, *, client_ip, remote_addr, user_agent, session_key):
        """Create (or auto-heal) a Stripe PaymentIntent for the order's winner.

        Raises OrderAccessDenied or OrderServiceError; returns the client-facing
        payment-intent payload on success.
        """
        if order.winner_id != user.id:
            log_action(
                user=user,
                action="CHECKOUT_ACCESS_DENIED",
                resource_type="Order",
                resource_id=order.id,
                ip_address=client_ip,
                user_agent=user_agent,
                metadata={
                    "requested_by": str(user.id),
                    "security_event": True,
                    "session_id": session_key,
                    "listing_id": str(order.winning_bid.listing_id),
                },
            )
            raise OrderAccessDenied()

        if order.fulfillment_status != "pending_payment":
            raise OrderServiceError("This order has already been paid.", status_code=400)

        # Auto-heal: if a prior PaymentIntent exists, check whether Stripe
        # already confirmed it (handles DB/webhook desync from a failed confirm).
        if order.stripe_payment_intent_id:
            try:
                prior = stripe_client.retrieve_payment_intent(order.stripe_payment_intent_id)
                if prior.get("status") == "succeeded":
                    order.fulfillment_status = "paid"
                    order.save(update_fields=["fulfillment_status", "updated_at"])
                    log_action(
                        user=user,
                        action="ORDER_PAID",
                        resource_type="Order",
                        resource_id=order.id,
                        ip_address=remote_addr,
                        user_agent=user_agent,
                        metadata={
                            "payment_intent": order.stripe_payment_intent_id,
                            "source": "auto_heal",
                            "session_id": session_key,
                            "listing_id": str(order.winning_bid.listing_id),
                        },
                    )
                    logger.info("Order %s auto-healed to paid (pi=%s)", order.id, order.stripe_payment_intent_id)
                    raise OrderServiceError("This order has already been paid.", status_code=400)
            except OrderServiceError:
                raise
            except Exception:
                pass  # Can't retrieve — proceed normally

        # Persist the delivery address snapshot if the winner supplied one.
        if delivery_address:
            order.delivery_address_snapshot = delivery_address
            order.save(update_fields=["delivery_address_snapshot", "updated_at"])

        # Prefer the persisted amount (source of truth); fall back to the bid
        # for any legacy row not yet backfilled.
        amount_cents = cls.amount_to_cents(order.amount or order.winning_bid.amount)

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
        order.ip_address = client_ip or None
        order.session_id = session_key or ""

        # Record the PaymentIntent id so the webhook can reconcile it later.
        update_fields = ["ip_address", "session_id", "updated_at"]
        if intent.get("id"):
            order.stripe_payment_intent_id = intent["id"]
            update_fields.append("stripe_payment_intent_id")
        order.save(update_fields=update_fields)

        log_action(
            user=user,
            action="CHECKOUT_INITIATED",
            resource_type="Order",
            resource_id=order.id,
            ip_address=remote_addr,
            user_agent=user_agent,
            metadata={
                "order_id": str(order.id),
                "amount_cents": amount_cents,
                "currency": settings.STRIPE_CURRENCY,
                "session_id": session_key,
                "listing_id": str(order.winning_bid.listing_id),
            },
        )

        return {
            "client_secret": intent["client_secret"],
            "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            "amount": amount_cents,
            "currency": intent["currency"],
            "demo": intent.get("demo", False),
        }

    @staticmethod
    def confirm_payment(order, user, payment_intent_id, *, client_ip, user_agent, session_key):
        """Verify and apply a client-confirmed Stripe payment.

        Called immediately after stripe.confirmPayment() succeeds on the
        frontend, eliminating the need for the Stripe CLI / webhook listener in
        development. The webhook remains a safety net for edge cases.

        Returns True if the order was already confirmed (no-op), False if this
        call marked it paid.
        """
        # Idempotent — already confirmed by webhook or a prior call.
        if order.fulfillment_status != "pending_payment":
            return True

        if not payment_intent_id:
            raise OrderServiceError("payment_intent_id is required.", status_code=400)

        # Retrieve and verify directly with Stripe — never trust the client's claim.
        try:
            intent = stripe_client.retrieve_payment_intent(payment_intent_id)
        except Exception as exc:
            logger.warning(
                "ConfirmPayment: retrieve failed pi=%s error=%s", payment_intent_id, exc
            )
            raise OrderServiceError("Could not verify payment with Stripe.", status_code=400)

        if not intent.get("demo"):
            if intent.get("status") != "succeeded":
                raise OrderServiceError("Payment has not completed.", status_code=400)

            # Cross-check metadata to ensure this PI was created for this order.
            metadata = intent.get("metadata", {})
            if str(metadata.get("order_id", "")) != str(order.id):
                logger.error(
                    "ConfirmPayment mismatch: pi=%s pi_order=%s req_order=%s user=%s",
                    payment_intent_id, metadata.get("order_id"), order.id, user.email,
                )
                log_action(
                    user=user,
                    action="PAYMENT_CONFIRM_MISMATCH",
                    resource_type="Order",
                    resource_id=order.id,
                    ip_address=client_ip,
                    metadata={
                        "payment_intent": payment_intent_id,
                        "security_event": True,
                        "session_id": session_key,
                        "listing_id": str(order.winning_bid.listing_id),
                    },
                )
                raise OrderServiceError("Payment does not match this order.", status_code=400)

        order.fulfillment_status = "paid"
        if not intent.get("demo"):
            order.stripe_payment_intent_id = payment_intent_id
        order.save(update_fields=["fulfillment_status", "stripe_payment_intent_id", "updated_at"])

        log_action(
            user=user,
            action="ORDER_PAID",
            resource_type="Order",
            resource_id=order.id,
            ip_address=client_ip,
            user_agent=user_agent,
            metadata={
                "payment_intent": payment_intent_id,
                "source": "direct_confirm",
                "session_id": session_key,
                "listing_id": str(order.winning_bid.listing_id),
            },
        )
        logger.info("Order %s paid via direct confirm (pi=%s)", order.id, payment_intent_id)
        return False

    @staticmethod
    def handle_payment_succeeded(intent, ip_address=None):
        """Reconcile a Stripe `payment_intent.succeeded` webhook event."""
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
                ip_address=ip_address,
                metadata={
                    "order_winner": str(order.winner_id),
                    "claimed_winner": str(claimed_winner_id),
                    "payment_intent": str(payment_intent_id),
                    "security_event": True,
                    # Server-to-server Stripe webhook — no browser session exists.
                    "session_id": None,
                    "listing_id": str(order.winning_bid.listing_id),
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
                ip_address=ip_address,
                metadata={
                    "payment_intent": str(payment_intent_id),
                    # Server-to-server Stripe webhook — no browser session exists.
                    "session_id": None,
                    "listing_id": str(order.winning_bid.listing_id),
                },
            )
            logger.info("Order %s marked paid via webhook", order.id)
