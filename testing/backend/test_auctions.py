"""Feature tests for the auctions endpoints."""
import asyncio
from datetime import timedelta

import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.utils import timezone

from auctions.consumers import BidConsumer, WS_CLOSE_AUCTION_ENDED
from auctions.models import Bid, Listing
from payments.models import Order

User = get_user_model()

LIST_URL = "/api/auctions/"
CREATE_URL = "/api/auctions/create/"
BID_HISTORY_URL = "/api/auctions/bids/history/"
DASHBOARD_URL = "/api/auctions/dashboard/"


@pytest.mark.django_db
def test_auction_list_accessible_without_auth(client):
    resp = client.get(LIST_URL)
    assert resp.status_code in (200, 501)


@pytest.mark.django_db
def test_users_can_see_ended_auctions_in_list(client, admin_user):
    now = timezone.now()
    
    ended_listing = Listing.objects.create(
        created_by=admin_user,
        title="Ended Auction",
        description="This auction has ended",
        image_key="",
        category="Others",
        starting_price="100.00",
        current_highest_bid="150.00",
        minimum_increment="5.00",
        starts_at=now - timedelta(days=2),
        ends_at=now - timedelta(hours=1),
        status="ended",
    )
    
    resp = client.get(LIST_URL)
    assert resp.status_code == 200
    
    data = resp.json()
    assert len(data) > 0
    assert any(item["id"] == str(ended_listing.id) for item in data)


@pytest.mark.django_db
def test_auction_list_search_filters_by_title(client, admin_user):
    now = timezone.now()
    common = dict(
        created_by=admin_user,
        description="desc",
        image_key="",
        starting_price="100.00",
        current_highest_bid="150.00",
        minimum_increment="5.00",
        starts_at=now - timedelta(days=2),
        ends_at=now - timedelta(hours=1),
        status="ended",
        category="Others",
    )
    matching = Listing.objects.create(title="Vintage Rolex Watch", **common)
    Listing.objects.create(title="Leather Handbag", **common)

    resp = client.get(LIST_URL, {"q": "rolex"})
    assert resp.status_code == 200
    data = resp.json()
    assert {item["id"] for item in data} == {str(matching.id)}


@pytest.mark.django_db
def test_auction_list_search_rejects_invalid_ordering(client):
    resp = client.get(LIST_URL, {"ordering": "'; DROP TABLE listings;--"})
    assert resp.status_code == 400


@pytest.mark.django_db
def test_users_can_view_ended_auction_details(client, admin_user):
    now = timezone.now()
    
    ended_listing = Listing.objects.create(
        created_by=admin_user,
        title="Ended Auction Details",
        description="This ended auction can be viewed by users",
        image_key="listings/ended.jpg",
        category="Watches",
        starting_price="500.00",
        current_highest_bid="750.00",
        minimum_increment="25.00",
        starts_at=now - timedelta(days=2),
        ends_at=now - timedelta(hours=1),
        status="ended",
    )
    
    resp = client.get(f"/api/auctions/{ended_listing.id}/")
    assert resp.status_code == 200
    
    data = resp.json()
    assert str(data["id"]) == str(ended_listing.id)
    assert data["title"] == "Ended Auction Details"
    assert data["status"] == "ended"


@pytest.mark.django_db
def test_scheduled_listing_hidden_from_list_for_non_staff(client, admin_user):
    now = timezone.now()

    scheduled_listing = Listing.objects.create(
        created_by=admin_user,
        title="Scheduled Auction",
        description="Not yet open for bidding",
        image_key="",
        category="Others",
        starting_price="100.00",
        current_highest_bid="100.00",
        minimum_increment="5.00",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=2),
        status="scheduled",
    )

    resp = client.get(LIST_URL)
    assert resp.status_code == 200
    data = resp.json()
    assert not any(item["id"] == str(scheduled_listing.id) for item in data)


@pytest.mark.django_db
def test_scheduled_listing_detail_returns_404_for_non_staff(client, admin_user):
    now = timezone.now()

    scheduled_listing = Listing.objects.create(
        created_by=admin_user,
        title="Scheduled Auction Details",
        description="Not yet open for bidding",
        image_key="",
        category="Others",
        starting_price="100.00",
        current_highest_bid="100.00",
        minimum_increment="5.00",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=2),
        status="scheduled",
    )

    resp = client.get(f"/api/auctions/{scheduled_listing.id}/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_create_listing_requires_authentication(client):
    resp = client.post(CREATE_URL, {}, format="json")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_listing_bids_require_auth(client, admin_user):
    now = timezone.now()
    listing = Listing.objects.create(
        created_by=admin_user,
        title="Live Auction",
        description="desc",
        image_key="",
        category="Others",
        starting_price="100.00",
        current_highest_bid="100.00",
        minimum_increment="5.00",
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=1),
        status="active",
    )

    resp = client.get(f"/api/auctions/{listing.id}/bids/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_listing_bids_visible_to_verified_user(auth_client, admin_user):
    now = timezone.now()
    listing = Listing.objects.create(
        created_by=admin_user,
        title="Live Auction",
        description="desc",
        image_key="",
        category="Others",
        starting_price="100.00",
        current_highest_bid="100.00",
        minimum_increment="5.00",
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=1),
        status="active",
    )

    resp = auth_client.get(f"/api/auctions/{listing.id}/bids/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_listing_accessible_when_authenticated(admin_client):
    resp = admin_client.post(CREATE_URL, {}, format="json")
    assert resp.status_code in (200, 201, 400, 501)


@pytest.mark.django_db
def test_bid_history_requires_authentication(client):
    resp = client.get(BID_HISTORY_URL)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_bid_history_accessible_when_authenticated(auth_client):
    resp = auth_client.get(BID_HISTORY_URL)
    assert resp.status_code in (200, 501)


@pytest.mark.django_db
def test_submit_bid_requires_authentication(client):
    import uuid
    url = f"/api/auctions/{uuid.uuid4()}/bid/"
    resp = client.post(url, {}, format="json")
    assert resp.status_code in (403, 404)


@pytest.mark.django_db
def test_submit_bid_success(auth_client, verified_user):
    now = timezone.now()
    other_user = User.objects.create_user(
        email="seller@example.com",
        display_name="Seller",
        password="StrongPass123!",
        is_active=True,
        is_email_verified=True,
    )
    listing = Listing.objects.create(
        created_by=other_user,
        title="Camera",
        description="Auction item",
        image_key="",
        category="Others",
        starting_price="100.00",
        current_highest_bid="100.00",
        minimum_increment="5.00",
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=2),
        status="active",
    )

    resp = auth_client.post(
        f"/api/auctions/{listing.id}/bid/",
        {"amount": "105.00"},
        format="json",
    )

    assert resp.status_code == 201
    payload = resp.json()
    assert payload["detail"] == "Bid submitted."
    assert payload["bid"]["amount"] == "105.00"

    listing.refresh_from_db()
    assert str(listing.current_highest_bid) == "105.00"


@pytest.mark.django_db
def test_submit_bid_rejects_amount_below_minimum_increment(auth_client):
    now = timezone.now()
    seller = User.objects.create_user(
        email="seller2@example.com",
        display_name="Seller 2",
        password="StrongPass123!",
        is_active=True,
        is_email_verified=True,
    )
    listing = Listing.objects.create(
        created_by=seller,
        title="Watch",
        description="Auction item",
        image_key="",
        category="Others",
        starting_price="300.00",
        current_highest_bid="340.00",
        minimum_increment="10.00",
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=2),
        status="active",
    )

    resp = auth_client.post(
        f"/api/auctions/{listing.id}/bid/",
        {"amount": "349.00"},
        format="json",
    )

    assert resp.status_code == 400
    assert "at least" in resp.json()["detail"]


@pytest.mark.django_db
def test_submit_bid_rejects_listing_owner(admin_client, admin_user):
    now = timezone.now()
    listing = Listing.objects.create(
        created_by=admin_user,
        title="Bag",
        description="Auction item",
        image_key="",
        category="Others",
        starting_price="80.00",
        current_highest_bid="80.00",
        minimum_increment="5.00",
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=2),
        status="active",
    )

    resp = admin_client.post(
        f"/api/auctions/{listing.id}/bid/",
        {"amount": "90.00"},
        format="json",
    )

    assert resp.status_code == 400
    assert "own listing" in resp.json()["detail"]


@pytest.mark.django_db
def test_submit_bid_rejects_admin_even_when_not_listing_owner(admin_client):
    now = timezone.now()
    seller = User.objects.create_user(
        email="seller3@example.com",
        display_name="Seller 3",
        password="StrongPass123!",
        is_active=True,
        is_email_verified=True,
    )
    listing = Listing.objects.create(
        created_by=seller,
        title="Headphones",
        description="Auction item",
        image_key="",
        category="Others",
        starting_price="150.00",
        current_highest_bid="150.00",
        minimum_increment="5.00",
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=2),
        status="active",
    )

    resp = admin_client.post(
        f"/api/auctions/{listing.id}/bid/",
        {"amount": "160.00"},
        format="json",
    )

    assert resp.status_code == 400
    assert "Admins cannot place bids." in resp.json()["detail"]


@pytest.mark.django_db
def test_submit_bid_rejects_consecutive_bids_from_same_user(auth_client, verified_user):
    now = timezone.now()
    seller = User.objects.create_user(
        email="seller4@example.com",
        display_name="Seller 4",
        password="StrongPass123!",
        is_active=True,
        is_email_verified=True,
    )
    listing = Listing.objects.create(
        created_by=seller,
        title="Laptop",
        description="Auction item",
        image_key="",
        category="Others",
        starting_price="900.00",
        current_highest_bid="900.00",
        minimum_increment="10.00",
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=2),
        status="active",
    )

    first_resp = auth_client.post(
        f"/api/auctions/{listing.id}/bid/",
        {"amount": "910.00"},
        format="json",
    )
    assert first_resp.status_code == 201

    second_resp = auth_client.post(
        f"/api/auctions/{listing.id}/bid/",
        {"amount": "920.00"},
        format="json",
    )

    assert second_resp.status_code == 400
    assert "consecutive bids" in second_resp.json()["detail"]


@pytest.mark.django_db
def test_submit_bid_rejects_ended_auction(auth_client):
    now = timezone.now()
    seller = User.objects.create_user(
        email="seller5@example.com",
        display_name="Seller 5",
        password="StrongPass123!",
        is_active=True,
        is_email_verified=True,
    )
    listing = Listing.objects.create(
        created_by=seller,
        title="Ended Camera",
        description="Auction already ended",
        image_key="",
        category="Others",
        starting_price="400.00",
        current_highest_bid="450.00",
        minimum_increment="10.00",
        starts_at=now - timedelta(hours=3),
        ends_at=now - timedelta(minutes=1),
        status="active",
    )

    resp = auth_client.post(
        f"/api/auctions/{listing.id}/bid/",
        {"amount": "460.00"},
        format="json",
    )

    assert resp.status_code == 400
    assert "active auctions" in resp.json()["detail"]

    listing.refresh_from_db()
    assert listing.status == "ended"


@pytest.mark.django_db(transaction=True)
def test_websocket_reconnect_is_rejected_after_auction_end(verified_user, admin_user):
    now = timezone.now()
    listing = Listing.objects.create(
        created_by=admin_user,
        title="Reconnect Closed Auction",
        description="Auction ended before websocket reconnect",
        image_key="",
        category="Others",
        starting_price="250.00",
        current_highest_bid="300.00",
        minimum_increment="10.00",
        starts_at=now - timedelta(hours=2),
        ends_at=now - timedelta(seconds=1),
        status="active",
    )

    async def attempt_reconnect():
        communicator = WebsocketCommunicator(BidConsumer.as_asgi(), f"/ws/auctions/{listing.id}/")
        communicator.scope["user"] = verified_user
        communicator.scope["url_route"] = {"kwargs": {"listing_id": str(listing.id)}}

        try:
            connected, _ = await communicator.connect()
            close_event = await communicator.receive_output(1)
            return connected, close_event
        finally:
            await communicator.wait()

    connected, close_event = asyncio.run(attempt_reconnect())
    assert connected is True
    assert close_event == {"type": "websocket.close", "code": WS_CLOSE_AUCTION_ENDED}

    listing.refresh_from_db()
    assert listing.status == "ended"


@pytest.mark.django_db
def test_listing_winner_is_persisted_once_auction_ends(admin_client, admin_user, verified_user):
    now = timezone.now()
    other_bidder = User.objects.create_user(
        email="second.bidder@example.com",
        display_name="Second Bidder",
        password="StrongPass123!",
        is_active=True,
        is_email_verified=True,
    )

    listing = Listing.objects.create(
        created_by=admin_user,
        title="Ended Listing",
        description="Auction ended",
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
        bidder=verified_user,
        anonymous_identifier="Bidder #1111",
        amount="130.00",
        is_winning=False,
    )
    Bid.objects.create(
        listing=listing,
        bidder=other_bidder,
        anonymous_identifier="Bidder #2222",
        amount="145.00",
        is_winning=False,
    )

    resp = admin_client.get(LIST_URL)
    assert resp.status_code == 200

    listing.refresh_from_db()
    assert listing.status == "ended"
    assert listing.winner_id == other_bidder.id
    assert str(listing.current_highest_bid) == "145.00"


@pytest.mark.django_db
def test_draft_listing_becomes_scheduled_when_completed_on_update(admin_client, admin_user):
    now = timezone.now()
    listing = Listing.objects.create(
        created_by=admin_user,
        title="Draft Listing",
        description="",
        image_key="",
        category="Others",
        starting_price="100.00",
        current_highest_bid="0.00",
        minimum_increment="1.00",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=2),
        status="draft",
    )

    payload = {
        "title": "Draft Listing Completed",
        "description": "All details now filled.",
        "image_key": "listings/item.jpg",
        "category": "Others",
        "starting_price": "120.00",
        "minimum_increment": "5.00",
        "starts_at": (now + timedelta(hours=2)).isoformat(),
        "ends_at": (now + timedelta(hours=5)).isoformat(),
        "save_as_draft": False,
    }

    resp = admin_client.patch(
        f"/api/auctions/{listing.id}/update/",
        payload,
        format="json",
    )

    assert resp.status_code == 200
    listing.refresh_from_db()
    assert listing.status == "scheduled"


@pytest.mark.django_db
@pytest.mark.django_db
def test_update_listing_allows_past_start_and_end_times(admin_client, admin_user):
    now = timezone.now()
    listing = Listing.objects.create(
        created_by=admin_user,
        title="Vintage Clock",
        description="Original description",
        image_key="listings/clock.jpg",
        category="Others",
        starting_price="300.00",
        current_highest_bid="300.00",
        minimum_increment="10.00",
        starts_at=now + timedelta(days=2),
        ends_at=now + timedelta(days=3),
        status="scheduled",
    )

    payload = {
        "title": "Vintage Clock Updated",
        "description": "Updated description",
        "image_key": "listings/clock-updated.jpg",
        "category": "Others",
        "starting_price": "320.00",
        "minimum_increment": "10.00",
        "starts_at": (now - timedelta(days=3)).isoformat(),
        "ends_at": (now - timedelta(days=2)).isoformat(),
        "save_as_draft": False,
    }

    resp = admin_client.patch(
        f"/api/auctions/{listing.id}/update/",
        payload,
        format="json",
    )

    assert resp.status_code == 200

    listing.refresh_from_db()
    assert listing.starts_at < now
    assert listing.ends_at < now
    assert listing.status == "ended"


@pytest.mark.django_db
def test_dashboard_requires_authentication(client):
    resp = client.get(DASHBOARD_URL)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_dashboard_returns_only_authenticated_user_data(auth_client, verified_user):
    now = timezone.now()

    other_user = User.objects.create_user(
        email="other@example.com",
        display_name="Other User",
        password="StrongPass123!",
        is_active=True,
        is_email_verified=True,
    )

    active_listing_user = Listing.objects.create(
        created_by=other_user,
        title="Active Listing (Mine)",
        description="active",
        image_key="",
        category="Others",
        starting_price="100.00",
        current_highest_bid="120.00",
        minimum_increment="5.00",
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=3),
        status="active",
    )
    Bid.objects.create(
        listing=active_listing_user,
        bidder=verified_user,
        anonymous_identifier="Bidder #1001",
        amount="120.00",
        is_winning=True,
    )

    active_listing_other = Listing.objects.create(
        created_by=verified_user,
        title="Active Listing (Other)",
        description="active-other",
        image_key="",
        category="Others",
        starting_price="200.00",
        current_highest_bid="225.00",
        minimum_increment="5.00",
        starts_at=now - timedelta(hours=2),
        ends_at=now + timedelta(hours=4),
        status="active",
    )
    Bid.objects.create(
        listing=active_listing_other,
        bidder=other_user,
        anonymous_identifier="Bidder #2002",
        amount="225.00",
        is_winning=True,
    )

    won_listing_user = Listing.objects.create(
        created_by=other_user,
        title="Won Listing (Mine)",
        description="won",
        image_key="",
        category="Others",
        starting_price="150.00",
        current_highest_bid="190.00",
        minimum_increment="5.00",
        starts_at=now - timedelta(days=1, hours=3),
        ends_at=now - timedelta(hours=3),
        status="ended",
        winner=verified_user,
    )
    winning_bid_user = Bid.objects.create(
        listing=won_listing_user,
        bidder=verified_user,
        anonymous_identifier="Bidder #3003",
        amount="190.00",
        is_winning=True,
    )
    Order.objects.create(
        winner=verified_user,
        winning_bid=winning_bid_user,
        fulfillment_status="pending_payment",
        delivery_address_snapshot="Address A",
    )

    won_listing_other = Listing.objects.create(
        created_by=verified_user,
        title="Won Listing (Other)",
        description="won-other",
        image_key="",
        category="Others",
        starting_price="300.00",
        current_highest_bid="360.00",
        minimum_increment="10.00",
        starts_at=now - timedelta(days=2),
        ends_at=now - timedelta(days=1),
        status="ended",
        winner=other_user,
    )
    winning_bid_other = Bid.objects.create(
        listing=won_listing_other,
        bidder=other_user,
        anonymous_identifier="Bidder #4004",
        amount="360.00",
        is_winning=True,
    )
    Order.objects.create(
        winner=other_user,
        winning_bid=winning_bid_other,
        fulfillment_status="paid",
        delivery_address_snapshot="Address B",
    )

    history_lost_listing = Listing.objects.create(
        created_by=other_user,
        title="History Lost (Mine Bid)",
        description="history",
        image_key="",
        category="Others",
        starting_price="75.00",
        current_highest_bid="102.00",
        minimum_increment="2.00",
        starts_at=now - timedelta(days=1, hours=1),
        ends_at=now - timedelta(hours=1),
        status="ended",
        winner=other_user,
    )
    Bid.objects.create(
        listing=history_lost_listing,
        bidder=verified_user,
        anonymous_identifier="Bidder #5005",
        amount="100.00",
        is_winning=False,
    )
    Bid.objects.create(
        listing=history_lost_listing,
        bidder=other_user,
        anonymous_identifier="Bidder #6006",
        amount="102.00",
        is_winning=True,
    )

    resp = auth_client.get(DASHBOARD_URL)
    assert resp.status_code == 200

    payload = resp.json()

    active_titles = {item["title"] for item in payload["active_bids"]}
    assert "Active Listing (Mine)" in active_titles
    assert "Active Listing (Other)" not in active_titles

    won_titles = {item["title"] for item in payload["won_auctions"]}
    assert "Won Listing (Mine)" in won_titles
    assert "Won Listing (Other)" not in won_titles

    payment_status = payload["payment_status"]
    assert payment_status["total_orders"] == 1
    assert payment_status["counts_by_status"]["pending_payment"] == 1
    assert payment_status["counts_by_status"]["paid"] == 0

    history_titles = {item["title"] for item in payload["auction_history"]}
    assert "Active Listing (Mine)" in history_titles
    assert "Won Listing (Mine)" in history_titles
    assert "History Lost (Mine Bid)" in history_titles
    assert "Active Listing (Other)" not in history_titles
    assert "Won Listing (Other)" not in history_titles


@pytest.mark.django_db
def test_dashboard_rejects_admin_access(admin_client):
    resp = admin_client.get(DASHBOARD_URL)
    assert resp.status_code == 403
    assert "Admins cannot access the bidder dashboard" in resp.json()["detail"]
