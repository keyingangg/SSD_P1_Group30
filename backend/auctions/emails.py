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
