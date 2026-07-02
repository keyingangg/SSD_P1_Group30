"""Feature tests for the authentication and account management flows."""
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core import mail

from accounts.tokens import (
    generate_email_verification_token,
    generate_password_reset_token,
    generate_staff_invite_token,
)
from accounts.models import EmailVerificationToken, PasswordResetToken

User = get_user_model()

REGISTER_URL = "/api/accounts/register/"
VERIFY_URL = "/api/accounts/verify-email/"
LOGIN_URL = "/api/accounts/login/"
LOGOUT_URL = "/api/accounts/logout/"
PROFILE_URL = "/api/accounts/profile/"
PASSWORD_RESET_URL = "/api/accounts/password-reset/"
PASSWORD_RESET_CONFIRM_URL = "/api/accounts/password-reset/confirm/"
STAFF_INVITE_URL = "/api/accounts/staff/invite/"
ACCEPT_INVITE_URL = "/api/accounts/staff/accept-invite/"
ADMIN_USERS_URL = "/api/accounts/admin/users/"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_register_new_user_returns_201(client):
    resp = client.post(REGISTER_URL, {"email": "new@example.com", "password": "StrongPass123!"}, format="json")
    assert resp.status_code == 201
    assert not User.objects.get(email="new@example.com").is_active


@pytest.mark.django_db
def test_register_sends_verification_email(client):
    client.post(REGISTER_URL, {"email": "new@example.com", "password": "StrongPass123!"}, format="json")
    assert len(mail.outbox) == 1
    assert "new@example.com" in mail.outbox[0].to


@pytest.mark.django_db
def test_register_duplicate_verified_email_returns_201_no_enumeration(verified_user, client):
    resp = client.post(REGISTER_URL, {"email": verified_user.email, "password": "StrongPass123!"}, format="json")
    assert resp.status_code == 201
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_register_duplicate_unverified_resends_link(client):
    client.post(REGISTER_URL, {"email": "pending@example.com", "password": "StrongPass123!"}, format="json")
    mail.outbox = []
    resp = client.post(REGISTER_URL, {"email": "pending@example.com", "password": "StrongPass123!"}, format="json")
    assert resp.status_code == 201
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_register_missing_fields_returns_400(client):
    resp = client.post(REGISTER_URL, {"email": "bad@example.com"}, format="json")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_verify_email_valid_token_activates_account(db):
    from rest_framework.test import APIClient
    c = APIClient()
    user = User.objects.create_user(
        email="v@example.com", display_name="V", password="StrongPass123!",
        is_active=False, is_email_verified=False,
    )
    raw_token = generate_email_verification_token(user)
    resp = c.post(VERIFY_URL, {"token": raw_token}, format="json")
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.is_active
    assert user.is_email_verified


@pytest.mark.django_db
def test_verify_email_invalid_token_returns_400(client):
    resp = client.post(VERIFY_URL, {"token": "notarealtoken"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_verify_email_expired_token_returns_400(db):
    from rest_framework.test import APIClient
    c = APIClient()
    user = User.objects.create_user(
        email="exp@example.com", display_name="E", password="StrongPass123!",
        is_active=False, is_email_verified=False,
    )
    raw_token = generate_email_verification_token(user)
    token_record = EmailVerificationToken.objects.get(user=user)
    token_record.expires_at = timezone.now() - timezone.timedelta(hours=1)
    token_record.save()
    resp = c.post(VERIFY_URL, {"token": raw_token}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_verify_email_used_token_returns_400(db):
    from rest_framework.test import APIClient
    c = APIClient()
    user = User.objects.create_user(
        email="used@example.com", display_name="U", password="StrongPass123!",
        is_active=False, is_email_verified=False,
    )
    raw_token = generate_email_verification_token(user)
    c.post(VERIFY_URL, {"token": raw_token}, format="json")
    resp = c.post(VERIFY_URL, {"token": raw_token}, format="json")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Login / logout
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_login_valid_credentials_returns_200(verified_user, client):
    resp = client.post(LOGIN_URL, {"email": verified_user.email, "password": "StrongPass123!"}, format="json")
    assert resp.status_code == 200
    assert resp.data["email"] == verified_user.email


@pytest.mark.django_db
def test_login_wrong_password_returns_400(verified_user, client):
    resp = client.post(LOGIN_URL, {"email": verified_user.email, "password": "WrongPass999!"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_login_unverified_account_returns_400(db, client):
    User.objects.create_user(
        email="unverified@example.com", display_name="UV", password="StrongPass123!",
        is_active=False, is_email_verified=False,
    )
    resp = client.post(LOGIN_URL, {"email": "unverified@example.com", "password": "StrongPass123!"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_login_missing_fields_returns_400(client):
    resp = client.post(LOGIN_URL, {"email": "x@example.com"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_logout_authenticated_returns_200(auth_client):
    resp = auth_client.post(LOGOUT_URL)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_logout_unauthenticated_returns_403(client):
    resp = client.post(LOGOUT_URL)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# User profile
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_profile_authenticated_returns_200(auth_client, verified_user):
    resp = auth_client.get(PROFILE_URL)
    assert resp.status_code == 200
    assert resp.data["email"] == verified_user.email


@pytest.mark.django_db
def test_profile_unauthenticated_returns_403(client):
    resp = client.get(PROFILE_URL)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_password_reset_request_existing_user_sends_email(verified_user, client):
    resp = client.post(PASSWORD_RESET_URL, {"email": verified_user.email}, format="json")
    assert resp.status_code == 200
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_password_reset_request_nonexistent_user_returns_200_no_email(client):
    resp = client.post(PASSWORD_RESET_URL, {"email": "nobody@example.com"}, format="json")
    assert resp.status_code == 200
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_password_reset_confirm_valid_token_updates_password(verified_user, client):
    raw_token = generate_password_reset_token(verified_user)
    new_password = "NewStrongPass456!"
    resp = client.post(PASSWORD_RESET_CONFIRM_URL, {"token": raw_token, "password": new_password}, format="json")
    assert resp.status_code == 200
    verified_user.refresh_from_db()
    assert verified_user.check_password(new_password)


@pytest.mark.django_db
def test_password_reset_confirm_invalid_token_returns_400(client):
    resp = client.post(PASSWORD_RESET_CONFIRM_URL, {"token": "badtoken", "password": "NewStrongPass456!"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_password_reset_confirm_expired_token_returns_400(verified_user, client):
    raw_token = generate_password_reset_token(verified_user)
    record = PasswordResetToken.objects.get(user=verified_user)
    record.expires_at = timezone.now() - timezone.timedelta(minutes=1)
    record.save()
    resp = client.post(PASSWORD_RESET_CONFIRM_URL, {"token": raw_token, "password": "NewStrongPass456!"}, format="json")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Staff invite
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_staff_invite_admin_returns_201(admin_client):
    resp = admin_client.post(STAFF_INVITE_URL, {"email": "newstaff@example.com"}, format="json")
    assert resp.status_code == 201
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_staff_invite_non_admin_returns_404(auth_client):
    resp = auth_client.post(STAFF_INVITE_URL, {"email": "newstaff@example.com"}, format="json")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_staff_invite_unauthenticated_returns_404(client):
    resp = client.post(STAFF_INVITE_URL, {"email": "newstaff@example.com"}, format="json")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_staff_invite_duplicate_email_returns_400(admin_client, verified_user):
    resp = admin_client.post(STAFF_INVITE_URL, {"email": verified_user.email}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_accept_invite_valid_token_activates_staff(admin_user, client):
    new_staff = User.objects.create_user(
        email="invited@example.com", display_name="Invited",
        password=None, is_active=False, is_staff=True, is_email_verified=False,
    )
    raw_token = generate_staff_invite_token(new_staff, invited_by=admin_user)
    resp = client.post(ACCEPT_INVITE_URL, {
        "token": raw_token,
        "display_name": "New Staff",
        "password": "StaffPass789!",
    }, format="json")
    assert resp.status_code == 200
    new_staff.refresh_from_db()
    assert new_staff.is_active
    assert new_staff.is_email_verified


@pytest.mark.django_db
def test_accept_invite_invalid_token_returns_400(client):
    resp = client.post(ACCEPT_INVITE_URL, {
        "token": "badtoken",
        "display_name": "Nobody",
        "password": "StaffPass789!",
    }, format="json")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Admin user management
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_admin_user_list_returns_200_for_staff(admin_client):
    resp = admin_client.get(ADMIN_USERS_URL)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_user_list_returns_404_for_regular_user(auth_client):
    resp = auth_client.get(ADMIN_USERS_URL)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_admin_user_detail_lock_toggles_is_active(admin_client, verified_user):
    url = f"/api/accounts/admin/users/{verified_user.pk}/"
    resp = admin_client.patch(url)
    assert resp.status_code == 200
    verified_user.refresh_from_db()
    assert not verified_user.is_active


@pytest.mark.django_db
def test_admin_cannot_lock_own_account(admin_client, admin_user):
    url = f"/api/accounts/admin/users/{admin_user.pk}/"
    resp = admin_client.patch(url)
    assert resp.status_code == 400


@pytest.mark.django_db
def test_admin_user_detail_delete_removes_user(admin_client, verified_user):
    url = f"/api/accounts/admin/users/{verified_user.pk}/"
    resp = admin_client.delete(url)
    assert resp.status_code == 200
    # Soft-delete: user row is kept with PII anonymised (NFSR-C-08 / SFR-05c).
    verified_user.refresh_from_db()
    assert verified_user.is_anonymised is True
    assert verified_user.is_active is False
    assert verified_user.email.startswith("deleted-")


@pytest.mark.django_db
def test_admin_user_detail_returns_404_for_regular_user(auth_client, admin_user):
    url = f"/api/accounts/admin/users/{admin_user.pk}/"
    resp = auth_client.patch(url)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_admin_terminate_sessions_clears_active_session(admin_client, verified_user):
    from rest_framework.test import APIClient

    user_client = APIClient()
    user_client.force_login(verified_user)
    assert "sessionid" in user_client.cookies

    url = f"/api/accounts/admin/users/{verified_user.pk}/terminate-sessions/"
    resp = admin_client.post(url)
    assert resp.status_code == 200

    from django.contrib.sessions.models import Session
    remaining = [
        s for s in Session.objects.all()
        if str(s.get_decoded().get("_auth_user_id")) == str(verified_user.pk)
    ]
    assert remaining == []


@pytest.mark.django_db
def test_admin_terminate_sessions_returns_404_for_regular_user(auth_client, admin_user):
    url = f"/api/accounts/admin/users/{admin_user.pk}/terminate-sessions/"
    resp = auth_client.post(url)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Account deletion — unpaid order guard (SFR-05b)
# ---------------------------------------------------------------------------

def _make_pending_order(winner):
    """Create a minimal ended listing -> winning bid -> pending_payment Order."""
    from auctions.models import Bid, Listing
    from payments.models import Order

    now = timezone.now()
    from datetime import timedelta
    seller = User.objects.create_user(
        email="seller-unpaid@example.com",
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
        current_highest_bid="150.00",
        minimum_increment="5.00",
        starts_at=now - timedelta(days=2),
        ends_at=now - timedelta(hours=1),
        status="ended",
        winner=winner,
    )
    bid = Bid.objects.create(
        listing=listing,
        bidder=winner,
        anonymous_identifier="Bidder #1",
        amount="150.00",
        is_winning=True,
    )
    return Order.objects.create(
        winner=winner,
        winning_bid=bid,
        fulfillment_status="pending_payment",
        delivery_address_snapshot="",
    )


@pytest.mark.django_db
def test_delete_account_blocked_with_unpaid_order(auth_client, verified_user):
    _make_pending_order(verified_user)

    resp = auth_client.post(
        "/api/accounts/delete/", {"current_password": "StrongPass123!"}, format="json"
    )
    assert resp.status_code == 400
    verified_user.refresh_from_db()
    assert verified_user.is_anonymised is False


@pytest.mark.django_db
def test_delete_account_succeeds_once_order_paid(auth_client, verified_user):
    order = _make_pending_order(verified_user)
    order.fulfillment_status = "paid"
    order.save(update_fields=["fulfillment_status"])

    resp = auth_client.post(
        "/api/accounts/delete/", {"current_password": "StrongPass123!"}, format="json"
    )
    assert resp.status_code == 200
    verified_user.refresh_from_db()
    assert verified_user.is_anonymised is True
