"""Feature tests for the payments endpoints."""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.utils import timezone

from auctions.models import Bid, Listing
from payments.models import Order

User = get_user_model()

CREATE_INTENT_URL = "/api/payments/create-intent/"
WEBHOOK_URL = "/api/payments/webhook/"


def _ended_listing_with_winner(seller, winner):
    """Create an ended listing with a single winning bid from `winner`."""
    now = timezone.now()
    listing = Listing.objects.create(
        created_by=seller,
        title="Retention Test Listing",
        description="Auction for payment-record tests",
        image_key="",
        category="Others",
        starting_price="100.00",
        current_highest_bid="100.00",
        minimum_increment="5.00",
        starts_at=now - timedelta(days=2),
        ends_at=now - timedelta(minutes=1),
        status="active",
    )
    Bid.objects.create(
        listing=listing,
        bidder=winner,
        anonymous_identifier="Bidder #4242",
        amount="150.00",
        is_winning=False,
    )
    return listing


@pytest.mark.django_db
def test_create_payment_intent_requires_authentication(client):
    resp = client.post(CREATE_INTENT_URL, {}, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_create_payment_intent_accessible_when_authenticated(auth_client):
    resp = auth_client.post(CREATE_INTENT_URL, {}, format="json")
    assert resp.status_code in (200, 400, 501)


@pytest.mark.django_db
def test_webhook_reachable_without_auth(client):
    resp = client.post(WEBHOOK_URL, {}, format="json")
    assert resp.status_code in (200, 400, 501)


@pytest.mark.django_db
def test_order_creation_on_close_populates_payment_record(admin_user, verified_user):
    """Finalizing an ended auction creates an Order with amount/currency/listing."""
    from django.conf import settings

    listing = _ended_listing_with_winner(admin_user, verified_user)
    listing.finalize_if_ended()

    order = Order.objects.get(winner=verified_user)
    assert str(order.amount) == "150.00"
    assert order.currency == settings.STRIPE_CURRENCY
    assert order.listing_id == listing.id


@pytest.mark.django_db
def test_checkout_populates_ip_and_session(auth_client, verified_user, admin_user):
    """Starting checkout records the requester's IP (and session key if any)."""
    listing = _ended_listing_with_winner(admin_user, verified_user)
    listing.finalize_if_ended()
    order = Order.objects.get(winner=verified_user)

    resp = auth_client.post(
        CREATE_INTENT_URL, {"order_id": str(order.id)}, format="json"
    )
    assert resp.status_code == 200

    order.refresh_from_db()
    assert order.ip_address is not None
    # session_id is captured (may be "" under token auth) but must not be None.
    assert order.session_id is not None


@pytest.mark.django_db
def test_deleting_user_with_order_is_blocked_by_protect(admin_user, verified_user):
    """Order.winner PROTECT prevents a hard user delete erasing payment history."""
    listing = _ended_listing_with_winner(admin_user, verified_user)
    listing.finalize_if_ended()
    assert Order.objects.filter(winner=verified_user).exists()

    with pytest.raises(ProtectedError):
        verified_user.delete()

    assert User.objects.filter(pk=verified_user.pk).exists()
    assert Order.objects.filter(winner=verified_user).exists()
