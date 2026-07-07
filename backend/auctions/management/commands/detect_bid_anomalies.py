"""Management command: flag anomalous bidding rates (FSR-AC-07 / NFSR-AC-05).

The 30/min per-user rate limit on BidSubmitView (django-ratelimit) already
throttles bid submissions; this command is a separate anomaly *alert*, not a
hard block — it flags users who placed an unusually high number of bids in
a short window so the pattern can be reviewed, even though each individual
bid was allowed through the rate limiter.

Run on a schedule (e.g. every few minutes via cron):
    python manage.py detect_bid_anomalies
    python manage.py detect_bid_anomalies --threshold 20 --window 1
    python manage.py detect_bid_anomalies --dry-run
"""
from django.core.management.base import BaseCommand

from auctions.business.bid_anomaly_detection import (
    alert_anomaly,
    find_anomalous_bidders,
    log_anomaly,
    notify_anomalous_bidder,
)


class Command(BaseCommand):
    help = "Flag bidders whose recent bid rate exceeds the anomaly threshold (NFSR-AC-05)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--threshold",
            type=int,
            default=20,
            help="Flag bidders with more than this many bids in the window (default: 20).",
        )
        parser.add_argument(
            "--window",
            type=int,
            default=1,
            help="Rolling window in minutes to count bids over (default: 1).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List flagged bidders without sending emails or writing audit logs.",
        )

    def handle(self, *args, **options):
        threshold = options["threshold"]
        window = options["window"]
        dry_run = options["dry_run"]

        flagged = find_anomalous_bidders(threshold, window)

        count = 0
        for row in flagged:
            count += 1
            bidder_id = row["bidder_id"]
            email = row["bidder__email"]
            bid_count = row["bid_count"]

            if dry_run:
                self.stdout.write(
                    f"[dry-run] bidder={bidder_id} email={email} bid_count={bid_count}"
                )
                continue

            try:
                notify_anomalous_bidder(email, bid_count, window)
            except Exception as exc:
                self.stderr.write(f"  Failed to email {email}: {exc}")

            log_anomaly(bidder_id, bid_count, window)

            try:
                alert_anomaly(bidder_id, email, bid_count, threshold, window)
            except Exception as exc:
                self.stderr.write(f"  Failed to send security alert for {email}: {exc}")

            self.stdout.write(f"  Flagged bidder={bidder_id} email={email} bid_count={bid_count}")

        style = self.style.WARNING if count else self.style.SUCCESS
        self.stdout.write(style(f"Done: {count} bidder(s) flagged."))
