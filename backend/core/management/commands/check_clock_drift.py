"""Management command: verify the host clock is synchronised to UTC via NTP.

All log timestamps (AuditLog.timestamp, Bid.submitted_at, auction closure
checks) are generated with django.utils.timezone.now(), which Django stores
as UTC in the database because USE_TZ=True. That guarantees every component
*agrees on what clock it is reading* only if the underlying host clock is
itself correct — if the OS clock has drifted, every timestamp it produces
drifts with it, which would break bid tie-break determinism and audit log
timeline ordering (NFSR-AC-06 / FSR-AC-08 / NFSR-IN-01).

This command queries an NTP server for the true time, compares it against
the local system clock, and raises a security alert if the drift exceeds
CLOCK_DRIFT_ALERT_THRESHOLD_SECONDS. It does not correct the clock — that is
the OS-level NTP client's (chrony / systemd-timesyncd / w32time) job; this is
a monitor that verifies that job is actually keeping up.

Run on a schedule (e.g. hourly cron):
    python manage.py check_clock_drift
    python manage.py check_clock_drift --server time.cloudflare.com
"""
import time

import ntplib
from django.conf import settings
from django.core.management.base import BaseCommand

from core.alerts import send_security_alert
from core.audit import log_action


class Command(BaseCommand):
    help = "Verify the host clock is synchronised to UTC via NTP (NFSR-AC-06)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--server",
            default=None,
            help="NTP server to query (default: settings.NTP_SERVER).",
        )

    def handle(self, *args, **options):
        server = options["server"] or settings.NTP_SERVER
        threshold = settings.CLOCK_DRIFT_ALERT_THRESHOLD_SECONDS

        client = ntplib.NTPClient()
        try:
            response = client.request(server, version=3, timeout=5)
        except Exception as exc:
            self.stderr.write(f"Failed to query NTP server {server}: {exc}")
            raise SystemExit(1)

        offset = response.offset
        local_time = time.time()

        self.stdout.write(
            f"NTP server={server} offset={offset:+.3f}s "
            f"(threshold={threshold}s) local_time={local_time}"
        )

        if abs(offset) <= threshold:
            self.stdout.write(self.style.SUCCESS("Clock is within NTP tolerance."))
            return

        message = (
            f"Host clock drift of {offset:+.3f}s detected against NTP server "
            f"{server}, exceeding the {threshold}s tolerance. Audit log and bid "
            "timestamps generated on this host may no longer be trustworthy for "
            "cross-system ordering or tie-breaking until the OS clock is "
            "resynchronised."
        )
        self.stderr.write(self.style.ERROR(message))

        try:
            send_security_alert(
                subject="Host clock drift exceeds NTP tolerance",
                message=message,
                severity="high",
                metadata={
                    "ntp_server": server,
                    "offset_seconds": offset,
                    "threshold_seconds": threshold,
                },
            )
            log_action(
                user=None,
                action="clock_drift_detected",
                resource_type="host",
                metadata={
                    "ntp_server": server,
                    "offset_seconds": offset,
                    "threshold_seconds": threshold,
                },
            )
        except Exception as exc:
            self.stderr.write(f"Failed to send security alert / audit log: {exc}")

        raise SystemExit(1)
