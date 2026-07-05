"""Feature tests for the TOTP/MFA flows (SFR-02b, NFSR-AU-01, NFSR-AU-04, NFSR-AC-02)."""
import time
import pytest
from binascii import unhexlify
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

User = get_user_model()

MFA_STATUS_URL = "/api/accounts/mfa/status/"
MFA_ENROL_URL = "/api/accounts/mfa/enrol/"
MFA_ENROL_CONFIRM_URL = "/api/accounts/mfa/enrol/confirm/"
MFA_UNENROL_URL = "/api/accounts/mfa/unenrol/"
MFA_LOGIN_VERIFY_URL = "/api/accounts/mfa/verify-login/"
LOGIN_URL = "/api/accounts/login/"
DELETE_ACCOUNT_URL = "/api/accounts/delete/"


def _current_token(device):
    """Return the current valid 6-digit TOTP code for a device."""
    key_bytes = unhexlify(device.key.encode())
    return str(totp(key_bytes, step=device.step, t0=device.t0, digits=device.digits, drift=device.drift)).zfill(device.digits)


def _make_device(user, confirmed=True):
    """Create a TOTPDevice for a user and return (device, valid_token)."""
    device = TOTPDevice.objects.create(user=user, name=user.email, confirmed=confirmed)
    token = _current_token(device)
    return device, token


# ---------------------------------------------------------------------------
# MFA status
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_mfa_status_unenrolled(auth_client):
    resp = auth_client.get(MFA_STATUS_URL)
    assert resp.status_code == 200
    assert resp.data["enrolled"] is False


@pytest.mark.django_db
def test_mfa_status_enrolled(auth_client, verified_user):
    _make_device(verified_user)
    resp = auth_client.get(MFA_STATUS_URL)
    assert resp.status_code == 200
    assert resp.data["enrolled"] is True


@pytest.mark.django_db
def test_mfa_status_unauthenticated_returns_403(client):
    resp = client.get(MFA_STATUS_URL)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Enrolment — begin
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_mfa_enrol_returns_qr_code(auth_client):
    resp = auth_client.get(MFA_ENROL_URL)
    assert resp.status_code == 200
    assert "qr_code" in resp.data
    assert len(resp.data["qr_code"]) > 0


@pytest.mark.django_db
def test_mfa_enrol_creates_unconfirmed_device(auth_client, verified_user):
    auth_client.get(MFA_ENROL_URL)
    assert TOTPDevice.objects.filter(user=verified_user, confirmed=False).exists()


@pytest.mark.django_db
def test_mfa_enrol_is_idempotent(auth_client, verified_user):
    auth_client.get(MFA_ENROL_URL)
    auth_client.get(MFA_ENROL_URL)
    # Should still be only one unconfirmed device
    assert TOTPDevice.objects.filter(user=verified_user, confirmed=False).count() == 1


@pytest.mark.django_db
def test_mfa_enrol_unauthenticated_returns_403(client):
    resp = client.get(MFA_ENROL_URL)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Enrolment — confirm (SFR-02b, NFSR-AU-01)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_mfa_enrol_confirm_valid_code_confirms_device(auth_client, verified_user):
    auth_client.get(MFA_ENROL_URL)
    device = TOTPDevice.objects.get(user=verified_user, confirmed=False)
    token = _current_token(device)

    resp = auth_client.post(MFA_ENROL_CONFIRM_URL, {"otp_code": token}, format="json")
    assert resp.status_code == 200
    device.refresh_from_db()
    assert device.confirmed is True


@pytest.mark.django_db
def test_mfa_enrol_confirm_invalid_code_returns_400(auth_client, verified_user):
    auth_client.get(MFA_ENROL_URL)
    resp = auth_client.post(MFA_ENROL_CONFIRM_URL, {"otp_code": "000000"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_mfa_enrol_confirm_no_pending_device_returns_400(auth_client):
    resp = auth_client.post(MFA_ENROL_CONFIRM_URL, {"otp_code": "123456"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_mfa_enrol_confirm_logs_audit_event(auth_client, verified_user):
    from core.models import AuditLog

    auth_client.get(MFA_ENROL_URL)
    device = TOTPDevice.objects.get(user=verified_user, confirmed=False)
    token = _current_token(device)

    auth_client.post(MFA_ENROL_CONFIRM_URL, {"otp_code": token}, format="json")

    assert AuditLog.objects.filter(user=verified_user, action="mfa_enrolled").exists()


# ---------------------------------------------------------------------------
# Unenrolment (NFSR-AC-02)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_mfa_unenrol_removes_device(auth_client, verified_user):
    _make_device(verified_user)
    resp = auth_client.post(MFA_UNENROL_URL)
    assert resp.status_code == 200
    assert not TOTPDevice.objects.filter(user=verified_user).exists()


@pytest.mark.django_db
def test_mfa_unenrol_not_enrolled_returns_400(auth_client):
    resp = auth_client.post(MFA_UNENROL_URL)
    assert resp.status_code == 400


@pytest.mark.django_db
def test_mfa_unenrol_logs_audit_event(auth_client, verified_user):
    from core.models import AuditLog

    _make_device(verified_user)
    auth_client.post(MFA_UNENROL_URL)

    assert AuditLog.objects.filter(user=verified_user, action="mfa_disabled").exists()


@pytest.mark.django_db
def test_mfa_unenrol_unauthenticated_returns_403(client):
    resp = client.post(MFA_UNENROL_URL)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Login with MFA (SFR-02b)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_login_with_mfa_enrolled_returns_mfa_required(verified_user, client):
    _make_device(verified_user)
    resp = client.post(LOGIN_URL, {"email": verified_user.email, "password": "StrongPass123!"}, format="json")
    assert resp.status_code == 200
    assert resp.data.get("mfa_required") is True


@pytest.mark.django_db
def test_login_without_mfa_returns_user_data(verified_user, client):
    resp = client.post(LOGIN_URL, {"email": verified_user.email, "password": "StrongPass123!"}, format="json")
    assert resp.status_code == 200
    assert "email" in resp.data
    assert "mfa_required" not in resp.data


@pytest.mark.django_db
def test_mfa_login_verify_valid_code_grants_session(verified_user, client):
    device, token = _make_device(verified_user)
    client.post(LOGIN_URL, {"email": verified_user.email, "password": "StrongPass123!"}, format="json")

    resp = client.post(MFA_LOGIN_VERIFY_URL, {"otp_code": token}, format="json")
    assert resp.status_code == 200
    assert resp.data["email"] == verified_user.email


@pytest.mark.django_db
def test_mfa_login_verify_invalid_code_returns_400(verified_user, client):
    _make_device(verified_user)
    client.post(LOGIN_URL, {"email": verified_user.email, "password": "StrongPass123!"}, format="json")

    resp = client.post(MFA_LOGIN_VERIFY_URL, {"otp_code": "000000"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_mfa_login_verify_without_pending_session_returns_400(client):
    resp = client.post(MFA_LOGIN_VERIFY_URL, {"otp_code": "123456"}, format="json")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Replay prevention — last_t (SFR-02b)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_totp_token_cannot_be_reused(verified_user, client):
    device, token = _make_device(verified_user)
    client.post(LOGIN_URL, {"email": verified_user.email, "password": "StrongPass123!"}, format="json")
    client.post(MFA_LOGIN_VERIFY_URL, {"otp_code": token}, format="json")

    # Log out and start a new MFA login attempt with the same token
    client.post("/api/accounts/logout/")
    _make_device(verified_user)  # re-enrol so login triggers MFA again
    client.post(LOGIN_URL, {"email": verified_user.email, "password": "StrongPass123!"}, format="json")
    resp = client.post(MFA_LOGIN_VERIFY_URL, {"otp_code": token}, format="json")
    # last_t prevents reuse within the same 30-second window
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Invalid attempts count toward django-axes (NFSR-AU-04)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_invalid_mfa_login_code_triggers_axes_signal(verified_user, client):
    _make_device(verified_user)
    client.post(LOGIN_URL, {"email": verified_user.email, "password": "StrongPass123!"}, format="json")

    with patch("accounts.views.user_login_failed") as mock_signal:
        client.post(MFA_LOGIN_VERIFY_URL, {"otp_code": "000000"}, format="json")
        mock_signal.send.assert_called_once()


@pytest.mark.django_db
def test_invalid_enrol_confirm_code_triggers_axes_signal(auth_client, verified_user):
    auth_client.get(MFA_ENROL_URL)
    with patch("accounts.views.user_login_failed") as mock_signal:
        auth_client.post(MFA_ENROL_CONFIRM_URL, {"otp_code": "000000"}, format="json")
        mock_signal.send.assert_called_once()


# ---------------------------------------------------------------------------
# Account deletion requires TOTP if enrolled (SFR-05a)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_delete_account_with_mfa_enrolled_requires_otp(auth_client, verified_user):
    _make_device(verified_user)
    resp = auth_client.post(DELETE_ACCOUNT_URL, {"current_password": "StrongPass123!"}, format="json")
    assert resp.status_code == 403
    assert resp.data.get("mfa_required") is True


@pytest.mark.django_db
def test_delete_account_with_mfa_valid_otp_succeeds(auth_client, verified_user):
    device, token = _make_device(verified_user)
    with patch("accounts.views.invalidate_all_user_sessions"):
        resp = auth_client.post(DELETE_ACCOUNT_URL, {"current_password": "StrongPass123!", "otp_code": token}, format="json")
    assert resp.status_code == 200
    # Soft-delete: user row is kept with PII anonymised (NFSR-C-08 / SFR-05c).
    verified_user.refresh_from_db()
    assert verified_user.is_anonymised is True
    assert verified_user.is_active is False


@pytest.mark.django_db
def test_delete_account_with_mfa_invalid_otp_returns_400(auth_client, verified_user):
    _make_device(verified_user)
    resp = auth_client.post(DELETE_ACCOUNT_URL, {"current_password": "StrongPass123!", "otp_code": "000000"}, format="json")
    assert resp.status_code == 400
    assert User.objects.filter(pk=verified_user.pk).exists()


@pytest.mark.django_db
def test_delete_account_without_mfa_succeeds_without_otp(auth_client, verified_user):
    with patch("accounts.views.invalidate_all_user_sessions"):
        resp = auth_client.post(DELETE_ACCOUNT_URL, {"current_password": "StrongPass123!"}, format="json")
    assert resp.status_code == 200
    # Soft-delete: user row is kept with PII anonymised (NFSR-C-08 / SFR-05c).
    verified_user.refresh_from_db()
    assert verified_user.is_anonymised is True
    assert verified_user.is_active is False
