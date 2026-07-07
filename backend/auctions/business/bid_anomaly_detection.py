"""Bid Anomaly Detection (diagram: business-layer box, Admin frame).

Flags bidders whose recent bid rate exceeds a threshold (FSR-AC-07 /
NFSR-AC-05). The 30/min per-user rate limit on BidSubmitView already
throttles submissions; this is a separate anomaly *alert*, not a hard
block -- each individual bid was allowed through the rate limiter, but an
unusually high rate over a short window is still worth flagging for review.

Invoked on a schedule by the detect_bid_anomalies management command.
"""
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from core.cross_cutting.alerts import send_security_alert
from core.cross_cutting.audit import log_action

from .emails import send_bid_anomaly_email
from ..data.models import Bid


def find_anomalous_bidders(threshold, window_minutes):
    """Return bidders whose bid count in the rolling window exceeds threshold."""
    cutoff = timezone.now() - timedelta(minutes=window_minutes)
    return (
        Bid.objects.filter(submitted_at__gte=cutoff, bidder__isnull=False)
        .values("bidder_id", "bidder__email")
        .annotate(bid_count=Count("id"))
        .filter(bid_count__gt=threshold)
    )


def notify_anomalous_bidder(email, bid_count, window_minutes):
    """Email the flagged bidder."""
    send_bid_anomaly_email(email, bid_count, window_minutes)


def log_anomaly(bidder_id, bid_count, window_minutes):
    """Record the anomaly in the audit trail."""
    log_action(
        user=None,
        action="bid_anomaly_detected",
        resource_type="User",
        resource_id=bidder_id,
        metadata={"bid_count": bid_count, "window_minutes": window_minutes},
    )


def alert_anomaly(bidder_id, email, bid_count, threshold, window_minutes):
    """Raise a security alert for the anomaly."""
    send_security_alert(
        subject="Excessive bid submission rate",
        message=(
            f"Bidder {email} ({bidder_id}) submitted {bid_count} bids "
            f"in the last {window_minutes} minute(s), exceeding the {threshold}/min threshold."
        ),
        severity="high",
        metadata={
            "bidder_id": str(bidder_id),
            "email": email,
            "bid_count": bid_count,
            "window_minutes": window_minutes,
            "threshold": threshold,
        },
    )
