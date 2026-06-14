"""Stripe client wrapper.

DEMO MODE: This module runs in Stripe test mode only. No real card processing
occurs. For the checkout demo, use Stripe test card 4242 4242 4242 4242 with any
future expiry date and any CVC to simulate a successful payment.
"""


def create_payment_intent(amount, currency, idempotency_key):
    """Create a payment intent.

    DEMO MODE: returns a hardcoded mock response for UI demonstration.
    Replace with a real stripe.PaymentIntent.create() call when going live.
    """
    # TODO: replace with real Stripe API call (test mode keys) when going live.
    return {
        "client_secret": "pi_mock_secret_demo_do_not_use_in_production",
        "amount": amount,
        "currency": currency,
        "status": "requires_payment_method",
        "demo": True,
    }


def verify_webhook_signature(payload, sig_header, secret):
    """Verify a Stripe webhook's HMAC-SHA256 signature.

    DEMO MODE: returns True for now.
    """
    # TODO: implement stripe.Webhook.construct_event signature verification.
    return True
