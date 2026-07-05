"""Tests for automated security alerting (NFSR-AC-05 / NFSR-AC-06 / NFSR-IN-07 / FSR-AC-07)."""
from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from accounts.models import AccountLockoutProfile
from accounts.signals import handle_user_locked_out
from auctions.models import Bid, Listing
from core.alerts import send_security_alert
from core.audit import log_action
from core.models import AuditLog
from core.security_monitoring import record_authz_denial


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
@override_settings(SECURITY_ALERT_EMAILS=["security@example.com"])
def test_send_security_alert_emails_configured_recipients():
    send_security_alert("Test alert", "Something happened", severity="high")

    assert len(mail.outbox) == 1
    assert "Test alert" in mail.outbox[0].subject
    assert mail.outbox[0].to == ["security@example.com"]


@pytest.mark.django_db
@override_settings(SECURITY_ALERT_EMAILS=[], ADMINS=[("Admin", "admin@example.com")])
def test_send_security_alert_falls_back_to_admins_when_no_recipients():
    send_security_alert("Test alert", "Something happened")

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["admin@example.com"]


@pytest.mark.django_db
@override_settings(SECURITY_ALERT_EMAILS=[])
def test_send_security_alert_never_raises_with_no_recipients_configured():
    # No SECURITY_ALERT_EMAILS and no ADMINS — must not raise, only log.
    send_security_alert("Test alert", "Something happened")


@pytest.mark.django_db
@override_settings(SECURITY_ALERT_EMAILS=["security@example.com"])
def test_account_lockout_sends_security_alert(verified_user):
    AccountLockoutProfile.objects.create(user=verified_user)

    handle_user_locked_out(
        sender=None,
        request=None,
        username=verified_user.email,
        ip_address="203.0.113.5",
    )

    subjects = [m.subject for m in mail.outbox]
    assert any("consecutive failed login attempts" in s for s in subjects)
    security_alert = next(m for m in mail.outbox if "consecutive failed login attempts" in m.subject)
    assert security_alert.to == ["security@example.com"]


@pytest.mark.django_db
@override_settings(SECURITY_ALERT_EMAILS=["security@example.com"])
def test_detect_bid_anomalies_sends_security_alert(verified_user, admin_user):
    now = timezone.now()
    listing = Listing.objects.create(
        created_by=admin_user,
        title="Test Item",
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
    for i in range(21):
        Bid.objects.create(
            listing=listing,
            bidder=verified_user,
            anonymous_identifier="Bidder #1",
            amount=100 + i,
        )

    call_command("detect_bid_anomalies", threshold=20, window=1)

    subjects = [m.subject for m in mail.outbox]
    assert any("Excessive bid submission rate" in s for s in subjects)
    assert AuditLog.objects.filter(action="bid_anomaly_detected").exists()


@pytest.mark.django_db
@override_settings(SECURITY_ALERT_EMAILS=["security@example.com"])
def test_verify_audit_log_hashes_alerts_immediately_on_mismatch():
    # audit_logs is append-only at the DB level (trigger blocks UPDATE/DELETE
    # entirely), so a mismatch can only be simulated at INSERT time — modeling
    # a row written through a path that bypassed log_action()'s hashing.
    AuditLog.objects.create(
        action="test_action",
        resource_type="x",
        row_hash="0" * 64,
        timestamp=timezone.now(),
    )

    with pytest.raises(SystemExit):
        call_command("verify_audit_log_hashes")

    subjects = [m.subject for m in mail.outbox]
    assert any("Audit log hash mismatch detected" in s for s in subjects)


@pytest.mark.django_db
@override_settings(SECURITY_ALERT_EMAILS=["security@example.com"])
def test_verify_audit_log_hashes_no_alert_when_all_rows_valid():
    log_action(user=None, action="test_action", resource_type="x")

    call_command("verify_audit_log_hashes")

    assert mail.outbox == []


@pytest.mark.django_db
@override_settings(
    SECURITY_ALERT_EMAILS=["security@example.com"],
    AUTHZ_DENIAL_ALERT_THRESHOLD=5,
    AUTHZ_DENIAL_ALERT_WINDOW_SECONDS=300,
)
def test_record_authz_denial_alerts_once_at_threshold():
    for _ in range(4):
        record_authz_denial(None, "198.51.100.7", view_name="AdminView", endpoint_path="/admin/")
    assert mail.outbox == []

    record_authz_denial(None, "198.51.100.7", view_name="AdminView", endpoint_path="/admin/")
    assert len(mail.outbox) == 1
    assert "Repeated denied authorisation attempts" in mail.outbox[0].subject

    # Further denials within the same window must not re-alert.
    record_authz_denial(None, "198.51.100.7", view_name="AdminView", endpoint_path="/admin/")
    assert len(mail.outbox) == 1

    assert AuditLog.objects.filter(action="authz_anomaly_detected").count() == 1


@pytest.mark.django_db
@override_settings(SECURITY_ALERT_EMAILS=["security@example.com"], CLOCK_DRIFT_ALERT_THRESHOLD_SECONDS=2.0)
def test_check_clock_drift_alerts_when_offset_exceeds_threshold():
    fake_response = Mock(offset=5.0)
    with patch("ntplib.NTPClient.request", return_value=fake_response):
        with pytest.raises(SystemExit):
            call_command("check_clock_drift")

    assert any("Host clock drift" in m.subject for m in mail.outbox)
    assert AuditLog.objects.filter(action="clock_drift_detected").exists()


@pytest.mark.django_db
@override_settings(SECURITY_ALERT_EMAILS=["security@example.com"], CLOCK_DRIFT_ALERT_THRESHOLD_SECONDS=2.0)
def test_check_clock_drift_no_alert_within_tolerance():
    fake_response = Mock(offset=0.1)
    with patch("ntplib.NTPClient.request", return_value=fake_response):
        call_command("check_clock_drift")

    assert mail.outbox == []
