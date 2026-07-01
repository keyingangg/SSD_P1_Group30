"""Feature tests for the payments / checkout flow.

Covers the security-critical behaviour of the checkout endpoints in
backend/payments/views.py:
  * PaymentIntent creation with IDOR protection (winner-only)
  * Direct payment confirmation (server-verified, never trusts the client)
  * Order detail access scoping (winner or admin only)
  * Admin-only order listing
  * Forward-only, admin-only fulfilment progression (FR-10)
  * Stripe webhook signature verification and winner cross-check

Stripe runs in demo/mock mode here — the test settings leave STRIPE_SECRET_KEY
blank, so stripe_client returns clearly-marked mock responses (see
backend/payments/stripe_client.py) and no real network calls are made.
"""
import json
import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from auctions.models import Bid, Listing
from core.models import AuditLog
from payments.models import Order

User = get_user_model()

CREATE_INTENT_URL = "/api/payments/create-intent/"
WEBHOOK_URL = "/api/payments/webhook/"
ORDERS_URL = "/api/payments/orders/"


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _make_order(winner, status="pending_payment", amount="150.00",
                 payment_intent_id=None):
    """Create a fully-linked ended listing -> winning bid -> Order for `winner`.

    The seller is a distinct throwaway user so the winner is never the listing
    owner. Returns the Order.
    """
    now = timezone.now()
    seller = User.objects.create_user(
        email=f"seller-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Seller",
        password="StrongPass123!",
        is_active=True,
        is_email_verified=True,
    )
    listing = Listing.objects.create(
        created_by=seller,
        title="Auction Item",
        description="An item that was won",
        image_key="",
        category="Others",
        starting_price="100.00",
        current_highest_bid=amount,
        minimum_increment="5.00",
        starts_at=now - timedelta(days=2),
        ends_at=now - timedelta(hours=1),
        status="ended",
        winner=winner,
    )
    bid = Bid.objects.create(
        listing=listing,
        bidder=winner,
        anonymous_identifier="Bidder #9999",
        amount=amount,
        is_winning=True,
    )
    return Order.objects.create(
        winner=winner,
        winning_bid=bid,
        fulfillment_status=status,
        delivery_address_snapshot="",
        stripe_payment_intent_id=payment_intent_id,
    )


def _other_user(tag):
    return User.objects.create_user(
        email=f"{tag}@example.com",
        display_name=tag,
        password="StrongPass123!",
        is_active=True,
        is_email_verified=True,
    )


# --------------------------------------------------------------------------
# CreatePaymentIntentView
# --------------------------------------------------------------------------
@pytest.mark.django_db
def test_create_payment_intent_requires_authentication(client):
    resp = client.post(CREATE_INTENT_URL, {}, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_create_payment_intent_winner_succeeds(auth_client, verified_user):
    order = _make_order(verified_user)

    fake_intent = {
        "id": "pi_fake_new",
        "client_secret": "pi_fake_new_secret",
        "amount": 15000,
        "currency": "sgd",
        "demo": True,
    }
    with patch("payments.stripe_client.create_payment_intent", return_value=fake_intent):
        resp = auth_client.post(
            CREATE_INTENT_URL, {"order_id": str(order.id)}, format="json"
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["amount"] == 15000


@pytest.mark.django_db
def test_create_payment_intent_persists_delivery_address(auth_client, verified_user):
    order = _make_order(verified_user)

    resp = auth_client.post(
        CREATE_INTENT_URL,
        {"order_id": str(order.id), "delivery_address": "1 Test Street, SG"},
        format="json",
    )

    assert resp.status_code == 200
    order.refresh_from_db()
    assert order.delivery_address_snapshot == "1 Test Street, SG"


@pytest.mark.django_db
def test_create_payment_intent_rejects_non_winner_idor(auth_client, verified_user):
    """IDOR: a user must not be able to pay for another user's order."""
    other_winner = _other_user("real-winner")
    order = _make_order(other_winner)

    resp = auth_client.post(
        CREATE_INTENT_URL, {"order_id": str(order.id)}, format="json"
    )

    assert resp.status_code == 403
    assert AuditLog.objects.filter(
        action="CHECKOUT_ACCESS_DENIED", resource_id=order.id
    ).exists()


@pytest.mark.django_db
def test_create_payment_intent_rejects_already_paid_order(auth_client, verified_user):
    order = _make_order(verified_user, status="paid")

    resp = auth_client.post(
        CREATE_INTENT_URL, {"order_id": str(order.id)}, format="json"
    )

    assert resp.status_code == 400
    assert "already been paid" in resp.json()["detail"]


@pytest.mark.django_db
def test_create_payment_intent_missing_order_returns_404(auth_client):
    resp = auth_client.post(
        CREATE_INTENT_URL, {"order_id": str(uuid.uuid4())}, format="json"
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_create_payment_intent_logs_checkout_initiated(auth_client, verified_user):
    order = _make_order(verified_user)

    resp = auth_client.post(
        CREATE_INTENT_URL, {"order_id": str(order.id)}, format="json"
    )

    assert resp.status_code == 200
    assert AuditLog.objects.filter(
        action="CHECKOUT_INITIATED", resource_id=order.id
    ).exists()


# --------------------------------------------------------------------------
# ConfirmPaymentView (direct, server-verified confirmation)
# --------------------------------------------------------------------------
@pytest.mark.django_db
def test_confirm_payment_winner_marks_order_paid(auth_client, verified_user):
    order = _make_order(verified_user)
    url = f"/api/payments/orders/{order.id}/confirm/"

    fake_intent = {
        "id": "pi_test_123",
        "status": "succeeded",
        "metadata": {"order_id": str(order.id)},
        "demo": False,
    }
    with patch("payments.stripe_client.retrieve_payment_intent", return_value=fake_intent):
        resp = auth_client.post(
            url, {"payment_intent_id": "pi_test_123"}, format="json"
        )

    assert resp.status_code == 200
    order.refresh_from_db()
    assert order.fulfillment_status == "paid"
    assert AuditLog.objects.filter(
        action="ORDER_PAID", resource_id=order.id
    ).exists()


@pytest.mark.django_db
def test_confirm_payment_rejects_non_winner(auth_client, verified_user):
    other_winner = _other_user("real-winner2")
    order = _make_order(other_winner)
    url = f"/api/payments/orders/{order.id}/confirm/"

    resp = auth_client.post(
        url, {"payment_intent_id": "pi_test_123"}, format="json"
    )

    assert resp.status_code == 403
    order.refresh_from_db()
    assert order.fulfillment_status == "pending_payment"


@pytest.mark.django_db
def test_confirm_payment_requires_payment_intent_id(auth_client, verified_user):
    order = _make_order(verified_user)
    url = f"/api/payments/orders/{order.id}/confirm/"

    resp = auth_client.post(url, {}, format="json")

    assert resp.status_code == 400
    assert "payment_intent_id is required" in resp.json()["detail"]


@pytest.mark.django_db
def test_confirm_payment_is_idempotent(auth_client, verified_user):
    order = _make_order(verified_user, status="paid")
    url = f"/api/payments/orders/{order.id}/confirm/"

    resp = auth_client.post(
        url, {"payment_intent_id": "pi_test_123"}, format="json"
    )

    assert resp.status_code == 200
    assert "already confirmed" in resp.json()["detail"]


@pytest.mark.django_db
def test_confirm_payment_rejects_mismatched_payment_intent(auth_client, verified_user):
    """The retrieved PaymentIntent's order_id metadata must match this order."""
    order = _make_order(verified_user)
    url = f"/api/payments/orders/{order.id}/confirm/"

    fake_intent = {
        "id": "pi_wrong_order",
        "status": "succeeded",
        "metadata": {"order_id": str(uuid.uuid4())},
        "demo": False,
    }
    with patch("payments.stripe_client.retrieve_payment_intent", return_value=fake_intent):
        resp = auth_client.post(
            url, {"payment_intent_id": "pi_wrong_order"}, format="json"
        )

    assert resp.status_code == 400
    assert "does not match this order" in resp.json()["detail"]
    order.refresh_from_db()
    assert order.fulfillment_status == "pending_payment"
    assert AuditLog.objects.filter(
        action="PAYMENT_CONFIRM_MISMATCH", resource_id=order.id
    ).exists()


# --------------------------------------------------------------------------
# OrderDetailView (read scoping)
# --------------------------------------------------------------------------
@pytest.mark.django_db
def test_order_detail_visible_to_winner(auth_client, verified_user):
    order = _make_order(verified_user)

    resp = auth_client.get(f"/api/payments/orders/{order.id}/")

    assert resp.status_code == 200
    assert resp.json()["id"] == str(order.id)


@pytest.mark.django_db
def test_order_detail_visible_to_admin(admin_client, verified_user):
    order = _make_order(verified_user)

    resp = admin_client.get(f"/api/payments/orders/{order.id}/")

    assert resp.status_code == 200


@pytest.mark.django_db
def test_order_detail_hidden_from_other_users(auth_client, verified_user):
    other_winner = _other_user("real-winner3")
    order = _make_order(other_winner)

    resp = auth_client.get(f"/api/payments/orders/{order.id}/")

    assert resp.status_code == 403
    assert AuditLog.objects.filter(
        action="ORDER_ACCESS_DENIED", resource_id=order.id
    ).exists()


# --------------------------------------------------------------------------
# AdminOrderListView
# --------------------------------------------------------------------------
@pytest.mark.django_db
def test_admin_order_list_requires_admin(auth_client, verified_user):
    _make_order(verified_user)
    resp = auth_client.get(ORDERS_URL)
    # IsAdminUser answers with 404 (silent) for non-staff callers.
    assert resp.status_code == 404


@pytest.mark.django_db
def test_admin_order_list_returns_orders(admin_client, verified_user):
    _make_order(verified_user)

    resp = admin_client.get(ORDERS_URL)

    assert resp.status_code == 200
    assert len(resp.json()) == 1


# --------------------------------------------------------------------------
# UpdateFulfillmentView (admin-only, forward-only -- FR-10)
# --------------------------------------------------------------------------
@pytest.mark.django_db
def test_update_fulfillment_requires_admin(auth_client, verified_user):
    order = _make_order(verified_user, status="paid")
    url = f"/api/payments/orders/{order.id}/fulfillment/"

    resp = auth_client.patch(url, {"fulfillment_status": "processing"}, format="json")

    assert resp.status_code == 404


@pytest.mark.django_db
def test_update_fulfillment_advances_one_step(admin_client, verified_user):
    order = _make_order(verified_user, status="paid")
    url = f"/api/payments/orders/{order.id}/fulfillment/"

    resp = admin_client.patch(url, {"fulfillment_status": "processing"}, format="json")

    assert resp.status_code == 200
    order.refresh_from_db()
    assert order.fulfillment_status == "processing"
    assert AuditLog.objects.filter(
        action="ORDER_FULFILLMENT_UPDATED", resource_id=order.id
    ).exists()


@pytest.mark.django_db
def test_update_fulfillment_rejects_skipping_a_step(admin_client, verified_user):
    """Forward-only: paid may go to processing, never straight to shipped."""
    order = _make_order(verified_user, status="paid")
    url = f"/api/payments/orders/{order.id}/fulfillment/"

    resp = admin_client.patch(url, {"fulfillment_status": "shipped"}, format="json")

    assert resp.status_code == 400
    order.refresh_from_db()
    assert order.fulfillment_status == "paid"


@pytest.mark.django_db
def test_update_fulfillment_rejects_moving_backwards(admin_client, verified_user):
    order = _make_order(verified_user, status="shipped")
    url = f"/api/payments/orders/{order.id}/fulfillment/"

    resp = admin_client.patch(url, {"fulfillment_status": "processing"}, format="json")

    assert resp.status_code == 400
    order.refresh_from_db()
    assert order.fulfillment_status == "shipped"


@pytest.mark.django_db
def test_update_fulfillment_rejects_pending_payment_to_paid(admin_client, verified_user):
    """pending_payment -> paid must go through the webhook, not this endpoint."""
    order = _make_order(verified_user, status="pending_payment")
    url = f"/api/payments/orders/{order.id}/fulfillment/"

    resp = admin_client.patch(url, {"fulfillment_status": "paid"}, format="json")

    assert resp.status_code == 400
    order.refresh_from_db()
    assert order.fulfillment_status == "pending_payment"


@pytest.mark.django_db
def test_update_fulfillment_rejects_terminal_state_advance(admin_client, verified_user):
    order = _make_order(verified_user, status="delivered")
    url = f"/api/payments/orders/{order.id}/fulfillment/"

    resp = admin_client.patch(url, {"fulfillment_status": "shipped"}, format="json")

    assert resp.status_code == 400
    order.refresh_from_db()
    assert order.fulfillment_status == "delivered"


# --------------------------------------------------------------------------
# StripeWebhookView (server-to-server)
# --------------------------------------------------------------------------
@pytest.mark.django_db
def test_webhook_rejects_invalid_signature(client):
    """With no valid signature, verification fails and nothing is written."""
    resp = client.post(
        WEBHOOK_URL,
        data=json.dumps({"type": "payment_intent.succeeded"}),
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="t=1,v1=deadbeef",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
@patch("payments.stripe_client.construct_webhook_event")
def test_webhook_marks_order_paid_on_success(mock_verify, client, verified_user):
    """A verified payment_intent.succeeded event marks the matching order paid."""
    order = _make_order(verified_user, payment_intent_id="pi_hook_success")
    payload = {
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_hook_success",
                "metadata": {"winner_id": str(order.winner_id)},
            }
        },
    }

    resp = client.post(
        WEBHOOK_URL,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="valid",
    )

    assert resp.status_code == 200
    order.refresh_from_db()
    assert order.fulfillment_status == "paid"
    assert AuditLog.objects.filter(
        action="ORDER_PAID", resource_id=order.id
    ).exists()


@pytest.mark.django_db
@patch("payments.stripe_client.construct_webhook_event")
def test_webhook_halts_on_winner_mismatch(mock_verify, client, verified_user):
    """If the event's winner metadata doesn't match the order, do NOT mark paid."""
    order = _make_order(verified_user, payment_intent_id="pi_hook_mismatch")
    payload = {
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_hook_mismatch",
                "metadata": {"winner_id": str(uuid.uuid4())},  # wrong winner
            }
        },
    }

    resp = client.post(
        WEBHOOK_URL,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="valid",
    )

    assert resp.status_code == 200
    order.refresh_from_db()
    assert order.fulfillment_status == "pending_payment"
    assert AuditLog.objects.filter(
        action="PAYMENT_WINNER_MISMATCH", resource_id=order.id
    ).exists()


@pytest.mark.django_db
@patch("payments.stripe_client.construct_webhook_event")
def test_webhook_ignores_unknown_payment_intent(mock_verify, client):
    """An event for a payment_intent with no matching order is a no-op, not an error."""
    payload = {
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_does_not_exist", "metadata": {}}},
    }

    resp = client.post(
        WEBHOOK_URL,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="valid",
    )

    assert resp.status_code == 200


@pytest.mark.django_db
@patch("payments.stripe_client.construct_webhook_event")
def test_webhook_payment_failed_does_not_mark_paid(mock_verify, client, verified_user):
    order = _make_order(verified_user, payment_intent_id="pi_hook_failed")
    payload = {
        "type": "payment_intent.payment_failed",
        "data": {"object": {"id": "pi_hook_failed", "metadata": {}}},
    }

    resp = client.post(
        WEBHOOK_URL,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="valid",
    )

    assert resp.status_code == 200
    order.refresh_from_db()
    assert order.fulfillment_status == "pending_payment"
