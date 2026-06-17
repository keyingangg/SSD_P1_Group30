"""Feature tests for the payments endpoints."""
import pytest

CREATE_INTENT_URL = "/api/payments/create-intent/"
WEBHOOK_URL = "/api/payments/webhook/"


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
