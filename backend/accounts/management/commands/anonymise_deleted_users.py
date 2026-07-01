"""Management command: anonymise PII for soft-deleted user accounts.

Run on a schedule (e.g. daily cron) to ensure no deleted account retains
PII beyond the 30-day retention window required by NFSR-C-08 / SFR-05c.

Accounts deleted via the API are anonymised immediately; this command acts
as a safety net for any accounts where anonymisation was not completed
(e.g. process crash mid-request, accounts pre-dating this implementation).

Usage:
    python manage.py anonymise_deleted_users
    python manage.py anonymise_deleted_users --days 0   # all non-anonymised deleted accounts
    python manage.py anonymise_deleted_users --dry-run
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.anonymisation import anonymise_user_data
from accounts.models import User


class Command(BaseCommand):
    help = "Anonymise PII for deleted user accounts not yet anonymised (NFSR-C-08)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Process accounts deleted at least N days ago (default: 30). Use 0 for all.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List affected accounts without making changes.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]

        qs = User.objects.filter(deleted_at__isnull=False, is_anonymised=False)
        if days > 0:
            cutoff = timezone.now() - timedelta(days=days)
            qs = qs.filter(deleted_at__lte=cutoff)

        count = qs.count()
        if dry_run:
            self.stdout.write(f"[dry-run] {count} account(s) would be anonymised.")
            for user in qs:
                self.stdout.write(f"  {user.id}  deleted_at={user.deleted_at}")
            return

        self.stdout.write(f"Anonymising {count} account(s)...")
        anonymised = 0
        errors = 0
        for user in qs:
            try:
                anonymise_user_data(user)
                anonymised += 1
                self.stdout.write(f"  OK  {user.id}")
            except Exception as exc:
                errors += 1
                self.stderr.write(f"  ERR {user.id}: {exc}")

        style = self.style.SUCCESS if errors == 0 else self.style.WARNING
        self.stdout.write(style(f"Done: {anonymised} anonymised, {errors} error(s)."))
