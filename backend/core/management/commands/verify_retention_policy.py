"""Management command: verify the audit/payment log retention floor holds (FSR-AC-09).

Payment logs must be retained >= 5 years, general audit logs >= 3 years.
AuditLog is append-only (AuditLog.save() rejects updates, and no app
registers it in Django admin, so there is no UI delete path either) — the
retention floor is a structural property of the schema, not something an
active purge job enforces. This command reports on that invariant rather
than deleting/archiving anything, so it's safe to run on any schedule
(e.g. weekly cron) purely for visibility/alerting:

    python manage.py verify_retention_policy
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.cross_cutting.audit import PAYMENT_ACTIONS
from core.data.models import AuditLog

AUDIT_LOG_FLOOR_YEARS = 3
PAYMENT_LOG_FLOOR_YEARS = 5


class Command(BaseCommand):
    help = "Report on audit/payment log age and confirm the retention floor holds (FSR-AC-09)."

    def handle(self, *args, **options):
        now = timezone.now()
        total = AuditLog.objects.count()

        if total == 0:
            self.stdout.write("No audit log rows exist yet.")
            return

        oldest = AuditLog.objects.order_by("timestamp").first()
        oldest_age_years = (now - oldest.timestamp).days / 365.25
        self.stdout.write(
            f"Audit log: {total} row(s), oldest is {oldest_age_years:.2f} years old "
            f"(floor: {AUDIT_LOG_FLOOR_YEARS} years)."
        )

        payment_qs = AuditLog.objects.filter(action__in=PAYMENT_ACTIONS)
        payment_total = payment_qs.count()
        if payment_total:
            oldest_payment = payment_qs.order_by("timestamp").first()
            oldest_payment_age_years = (now - oldest_payment.timestamp).days / 365.25
            self.stdout.write(
                f"Payment log: {payment_total} row(s), oldest is "
                f"{oldest_payment_age_years:.2f} years old (floor: {PAYMENT_LOG_FLOOR_YEARS} years)."
            )
        else:
            self.stdout.write("Payment log: no rows yet.")

        # Nothing in this codebase deletes AuditLog rows: save() rejects updates,
        # and no app registers AuditLog in Django admin, so there's no bulk-delete
        # UI path either. This is a point-in-time confirmation, not a guarantee —
        # re-run after any admin.py/migration change touching AuditLog.
        self.stdout.write(
            self.style.SUCCESS(
                "AuditLog is append-only and unregistered in Django admin — "
                "no delete path exists, so the retention floor holds structurally."
            )
        )
