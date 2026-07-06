"""Validate that a planned maintenance window does not overlap auction activity.

NFSR-AV-01 requires maintenance to be scheduled outside active auction windows.
This command checks a proposed downtime window against listing auction windows.

Examples:
    python manage.py check_maintenance_window --start 2026-07-10T01:00:00+08:00 --end 2026-07-10T02:00:00+08:00
    python manage.py check_maintenance_window --start 2026-07-10T01:00:00Z --end 2026-07-10T02:00:00Z --limit 20
    python manage.py check_maintenance_window --start 2026-07-10T01:00:00+08:00 --end 2026-07-10T02:00:00+08:00 --simulate clear
    python manage.py check_maintenance_window --start 2026-07-10T01:00:00+08:00 --end 2026-07-10T02:00:00+08:00 --simulate overlap
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from auctions.models import Listing


class Command(BaseCommand):
    help = (
        "Validate that a maintenance window does not overlap any non-cancelled "
        "auction window ."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--start",
            required=True,
            help="Maintenance start datetime in ISO-8601 format.",
        )
        parser.add_argument(
            "--end",
            required=True,
            help="Maintenance end datetime in ISO-8601 format.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Max overlapping listings to print (default: 10).",
        )
        parser.add_argument(
            "--simulate",
            choices=["clear", "overlap"],
            help=(
                "Simulation mode for dry-testing without database checks: "
                "'clear' prints an eligible result, 'overlap' prints a blocked result."
            ),
        )

    def _parse_ts(self, value, label):
        dt = parse_datetime(value)
        if dt is None:
            raise CommandError(
                f"Invalid {label} datetime '{value}'. Use ISO-8601, for example: 2026-07-10T01:00:00+08:00"
            )

        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    def handle(self, *args, **options):
        start_dt = self._parse_ts(options["start"], "start")
        end_dt = self._parse_ts(options["end"], "end")
        limit = max(int(options["limit"]), 1)
        simulate_mode = options.get("simulate")

        if end_dt <= start_dt:
            raise CommandError("--end must be later than --start.")

        if simulate_mode == "clear":
            self.stdout.write(
                self.style.WARNING(
                    "SIMULATION MODE: No database query executed."
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "OK: No auction window overlap detected. Maintenance window is eligible."
                )
            )
            return

        if simulate_mode == "overlap":
            self.stdout.write(
                self.style.WARNING(
                    "SIMULATION MODE: No database query executed."
                )
            )
            fake_count = max(limit, 2)
            self.stdout.write(
                self.style.ERROR(
                    f"BLOCKED: {fake_count} listing(s) overlap the maintenance window "
                    f"{start_dt.isoformat()} to {end_dt.isoformat()}."
                )
            )
            for idx in range(1, min(limit, fake_count) + 1):
                self.stdout.write(
                    "- "
                    f"id=SIM-{idx:03d} "
                    "status=active "
                    f"starts_at={start_dt.isoformat()} "
                    f"ends_at={end_dt.isoformat()} "
                    f"title=Simulated Listing {idx:03d}"
                )
            raise CommandError(
                "Choose a different maintenance window outside auction activity."
            )

        overlaps = (
            Listing.objects.exclude(status__in=["draft", "cancelled"])
            .filter(starts_at__lt=end_dt, ends_at__gt=start_dt)
            .order_by("starts_at")
        )

        overlap_count = overlaps.count()

        if overlap_count:
            self.stdout.write(
                self.style.ERROR(
                    f"BLOCKED: {overlap_count} listing(s) overlap the maintenance window "
                    f"{start_dt.isoformat()} to {end_dt.isoformat()}."
                )
            )

            for listing in overlaps[:limit]:
                self.stdout.write(
                    "- "
                    f"id={listing.id} "
                    f"status={listing.status} "
                    f"starts_at={listing.starts_at.isoformat() if listing.starts_at else 'null'} "
                    f"ends_at={listing.ends_at.isoformat() if listing.ends_at else 'null'} "
                    f"title={listing.title}"
                )

            raise CommandError(
                "Choose a different maintenance window outside auction activity."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "OK: No auction window overlap detected. Maintenance window is eligible."
            )
        )
