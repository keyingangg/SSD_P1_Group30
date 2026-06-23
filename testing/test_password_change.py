"""Tests for the in-session voluntary password change feature (PasswordChangeView)."""
import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model

User = get_user_model()

PASSWORD_CHANGE_URL = "/api/accounts/password-change/"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_password_change_valid_returns_200(auth_client):
    resp = auth_client.post(
        PASSWORD_CHANGE_URL,
        {"current_password": "StrongPass123!", "new_password": "NewStrongPass456!"},
        format="json",
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_password_change_updates_password_in_db(auth_client, verified_user):
    auth_client.post(
        PASSWORD_CHANGE_URL,
        {"current_password": "StrongPass123!", "new_password": "NewStrongPass456!"},
        format="json",
    )
    verified_user.refresh_from_db()
    assert verified_user.check_password("NewStrongPass456!")


@pytest.mark.django_db
def test_password_change_old_password_no_longer_works(auth_client, verified_user):
    auth_client.post(
        PASSWORD_CHANGE_URL,
        {"current_password": "StrongPass123!", "new_password": "NewStrongPass456!"},
        format="json",
    )
    verified_user.refresh_from_db()
    assert not verified_user.check_password("StrongPass123!")


# ---------------------------------------------------------------------------
# Authentication / authorisation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_password_change_unauthenticated_returns_403(client):
    resp = client.post(
        PASSWORD_CHANGE_URL,
        {"current_password": "StrongPass123!", "new_password": "NewStrongPass456!"},
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_password_change_unverified_user_returns_403(client, db):
    unverified = User.objects.create_user(
        email="unverified@example.com",
        display_name="Unverified",
        password="StrongPass123!",
        is_active=False,
        is_email_verified=False,
    )
    client.force_login(unverified)
    resp = client.post(
        PASSWORD_CHANGE_URL,
        {"current_password": "StrongPass123!", "new_password": "NewStrongPass456!"},
        format="json",
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_password_change_wrong_current_password_returns_400(auth_client):
    resp = auth_client.post(
        PASSWORD_CHANGE_URL,
        {"current_password": "WrongPassword99!", "new_password": "NewStrongPass456!"},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_password_change_missing_fields_returns_400(auth_client):
    resp = auth_client.post(PASSWORD_CHANGE_URL, {}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_password_change_new_password_too_short_returns_400(auth_client):
    resp = auth_client.post(
        PASSWORD_CHANGE_URL,
        {"current_password": "StrongPass123!", "new_password": "Short1!"},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_password_change_new_password_too_long_returns_400(auth_client):
    resp = auth_client.post(
        PASSWORD_CHANGE_URL,
        {"current_password": "StrongPass123!", "new_password": "A" * 129},
        format="json",
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# HIBP breach check
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_password_change_breached_password_returns_400(auth_client):
    with patch("accounts.views.is_password_breached", return_value=True):
        resp = auth_client.post(
            PASSWORD_CHANGE_URL,
            {"current_password": "StrongPass123!", "new_password": "NewStrongPass456!"},
            format="json",
        )
    assert resp.status_code == 400
    assert "breach" in resp.data["detail"].lower()
