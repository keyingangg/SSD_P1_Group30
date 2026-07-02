"""Transactional email helpers for the auctions app."""
from django.conf import settings
from django.core.mail import send_mail


def send_auction_cancelled_email(bidder_email, listing):
    """Notify a bidder that an auction they participated in has been cancelled.

    Called when an admin cancels a listing that has received at least one bid
    (SFR-06c).  All bids on the listing are void; the bidder owes nothing.
    """
    site = settings.SITE_NAME
    subject = f"Auction cancelled: {listing.title}"
    message = (
        f"Hi,\n\n"
        f"The auction for \"{listing.title}\" on {site} has been cancelled by "
        f"the organiser.\n\n"
        "Any bids you placed on this item are void and no payment will be "
        "taken.\n\n"
        "We apologise for any inconvenience.\n\n"
        f"— The {site} Team"
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [bidder_email],
        fail_silently=False,
    )


def send_bid_anomaly_email(bidder_email, bid_count, window_minutes):
    """Alert a bidder (and leave a record) that their bidding rate looked anomalous.

    Sent by the detect_bid_anomalies management command (FSR-AC-07 / NFSR-AC-05)
    when a user places an unusually high number of bids in a short window —
    the 30/min rate limit already throttles submissions; this flags the
    pattern for review rather than blocking it outright.
    """
    site = settings.SITE_NAME
    subject = f"Unusual bidding activity on your {site} account"
    message = (
        f"We noticed {bid_count} bids placed from your account in the last "
        f"{window_minutes} minute(s), which is higher than expected.\n\n"
        "If this was you, no action is needed. If you did not place these "
        "bids, please contact support and consider changing your password.\n\n"
        f"— The {site} Team"
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [bidder_email],
        fail_silently=False,
    )
