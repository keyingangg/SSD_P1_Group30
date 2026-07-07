"""Security alert delivery to the internal security/ops team.

Distinct from accounts/emails.py and auctions/emails.py, which notify the
*affected end user* (e.g. "your account was locked"). This module notifies
whoever is on call for the platform (NFSR-AC-05 / NFSR-AC-06 / NFSR-IN-07 /
FSR-AC-07): consecutive failed logins, bid-rate anomalies, denied-authorisation
bursts, audit log hash mismatches, and clock drift.

Delivery is best-effort on every channel independently — a failed webhook
must not suppress the email, and neither may raise back into the caller,
since alerting a security team about an anomaly must never itself become a
new way to break the request/command that detected it.
"""
import json
import logging

import requests
from django.conf import settings
from django.core.mail import mail_admins, send_mail

logger = logging.getLogger("security_alerts")


def send_security_alert(subject: str, message: str, *, severity: str = "high", metadata: dict | None = None) -> None:
    """Notify the security team of a detected anomaly.

    Always logged at ERROR level regardless of email/webhook delivery, so the
    alert is never silently lost even if no recipients are configured.
    """
    full_subject = f"[SecureBid security alert:{severity}] {subject}"
    body = message
    if metadata:
        body = f"{message}\n\nDetails:\n{json.dumps(metadata, default=str, indent=2)}"

    logger.error("%s :: %s", full_subject, body)

    recipients = settings.SECURITY_ALERT_EMAILS
    if recipients:
        try:
            send_mail(
                full_subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                recipients,
                fail_silently=False,
            )
        except Exception:
            logger.exception("Failed to email security alert %r to %r", subject, recipients)
    else:
        # No explicit distribution list configured — fall back to Django's
        # ADMINS setting via mail_admins so alerts are never dropped entirely.
        try:
            mail_admins(full_subject, body, fail_silently=True)
        except Exception:
            logger.exception("Failed to mail_admins security alert %r", subject)

    webhook_url = settings.SECURITY_ALERT_WEBHOOK_URL
    if webhook_url:
        try:
            requests.post(
                webhook_url,
                json={"text": f"*{full_subject}*\n{body}"},
                timeout=5,
            )
        except requests.RequestException:
            logger.exception("Failed to POST security alert %r to webhook", subject)
