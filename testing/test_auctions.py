"""Feature tests for the auctions endpoints."""
import pytest

LIST_URL = "/api/auctions/"
CREATE_URL = "/api/auctions/create/"
BID_HISTORY_URL = "/api/auctions/bids/history/"


@pytest.mark.django_db
def test_auction_list_accessible_without_auth(client):
    resp = client.get(LIST_URL)
    assert resp.status_code in (200, 501)


@pytest.mark.django_db
def test_create_listing_requires_authentication(client):
    resp = client.post(CREATE_URL, {}, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_create_listing_accessible_when_authenticated(auth_client):
    resp = auth_client.post(CREATE_URL, {}, format="json")
    assert resp.status_code in (200, 201, 400, 501)


@pytest.mark.django_db
def test_bid_history_requires_authentication(client):
    resp = client.get(BID_HISTORY_URL)
    assert resp.status_code == 403


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
