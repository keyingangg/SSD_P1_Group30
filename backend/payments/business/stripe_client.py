"""Stripe client wrapper.

Runs in Stripe test/sandbox mode — set STRIPE_SECRET_KEY to an sk_test_... key.
No real card processing occurs in test mode. For the checkout demo, use Stripe
test card 4242 4242 4242 4242 with any future expiry date and any CVC to
simulate a successful payment.

If no STRIPE_SECRET_KEY is configured the module falls back to a clearly-marked
mock response so the app still runs in local development without keys. The mock
client_secret will NOT work with the real Stripe.js card form — configure test
keys to exercise the full flow.
"""
import json
import logging

import stripe
from django.conf import settings

logger = logging.getLogger("securebid")


def _configured():
    """Return True if a real Stripe secret key is available."""
    return bool(settings.STRIPE_SECRET_KEY)


def create_payment_intent(amount_cents, currency, idempotency_key, metadata=None):
    """Create a Stripe PaymentIntent.

    amount_cents must be a positive integer in the smallest currency unit
    (e.g. cents for SGD). The idempotency_key prevents duplicate charges if the
    request is retried. Returns a dict with client_secret, amount, currency,
    status, and a `demo` flag.
    """
    if not _configured():
        # Mock fallback for environments without Stripe keys configured.
        logger.warning(
            "STRIPE_SECRET_KEY not set — returning mock payment intent. "
            "Configure test keys to exercise the real checkout flow."
        )
        return {
            "client_secret": None,
            "amount": amount_cents,
            "currency": currency,
            "status": "requires_payment_method",
            "demo": True,
        }

    stripe.api_key = settings.STRIPE_SECRET_KEY
    intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency=currency,
        metadata=metadata or {},
        automatic_payment_methods={"enabled": True},
        idempotency_key=str(idempotency_key),
    )
    return {
        "id": intent.id,
        "client_secret": intent.client_secret,
        "amount": intent.amount,
        "currency": intent.currency,
        "status": intent.status,
        "demo": False,
    }


def retrieve_payment_intent(payment_intent_id):
    """Retrieve a PaymentIntent from Stripe and return key fields as a plain dict.

    Used by the direct-confirm endpoint so the frontend can mark an order paid
    immediately after stripe.confirmPayment() succeeds, without needing the
    Stripe CLI or a webhook listener running locally.
    """
    if not _configured():
        return {"id": payment_intent_id, "status": "succeeded", "metadata": {}, "demo": True}

    stripe.api_key = settings.STRIPE_SECRET_KEY
    intent_obj = stripe.PaymentIntent.retrieve(payment_intent_id)
    # Parse the raw HTTP response body → guaranteed plain Python dict.
    # Same approach as the webhook handler to avoid Stripe SDK v5 object quirks.
    intent = json.loads(intent_obj.last_response.body)
    return {
        "id": intent["id"],
        "status": intent["status"],
        "metadata": intent.get("metadata") or {},
    }


def construct_webhook_event(payload, sig_header):
    """Verify a Stripe webhook's HMAC-SHA256 signature and parse the event.

    payload must be the raw request body (bytes). Raises ValueError on an
    invalid payload and stripe.error.SignatureVerificationError on a bad
    signature — the caller maps both to HTTP 400 and writes nothing to the DB.
    """
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )
