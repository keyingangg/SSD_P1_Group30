"""Assert the audit/payment log retention floor still holds.

Read-only / assertive: this command never deletes. It verifies that the
append-only guarantee on ``audit_logs`` is intact (so the >= 3 year / >= 5 year
minimum retention floors defined in settings are structurally enforced) and
reports counts and the oldest/newest timestamps for general and payment logs.

Exits non-zero with a clear message on any failure so it can gate CI/ops. It
complements the scheduled SHA-256 hash-verify job and can run on the same
cadence. See docs/RETENTION_POLICY.md.

    python manage.py verify_retention
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from core.audit import PAYMENT_ACTIONS, PAYMENT_RESOURCE_TYPES
from core.models import AuditLog

TRIGGER_NAME = "prevent_audit_update_delete"
AUDIT_TABLE = "audit_logs"


class Command(BaseCommand):
    help = "Verify the audit/payment log append-only retention floor is intact."

    def handle(self, *args, **options):
        failures = []

        # 1. The append-only trigger must exist on audit_logs.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM pg_trigger t
                JOIN pg_class c ON c.oid = t.tgrelid
                WHERE c.relname = %s AND t.tgname = %s AND NOT t.tgisinternal
                """,
                [AUDIT_TABLE, TRIGGER_NAME],
            )
            if cursor.fetchone():
                self.stdout.write(self.style.SUCCESS(
                    f"OK   append-only trigger '{TRIGGER_NAME}' present on {AUDIT_TABLE}"
                ))
            else:
                failures.append(
                    f"append-only trigger '{TRIGGER_NAME}' MISSING on {AUDIT_TABLE}"
                )

        # 2. A DELETE must be blocked. Attempt one against a real row inside a
        #    rolled-back transaction so nothing is ever actually removed. The
        #    row-level trigger fires for every role (including superuser), so
        #    this is the primary gate; the REVOKE grant is a secondary defence.
        delete_blocked = self._delete_is_blocked()

        if delete_blocked:
            self.stdout.write(self.style.SUCCESS(
                f"OK   DELETE on {AUDIT_TABLE} is blocked (append-only enforced)"
            ))
        else:
            failures.append(
                f"DELETE on {AUDIT_TABLE} was NOT blocked — append-only floor breached"
            )

        # 3. Report counts and oldest/newest timestamps, split by log class.
        payment_qs = AuditLog.objects.filter(
            action__in=PAYMENT_ACTIONS
        ) | AuditLog.objects.filter(resource_type__in=PAYMENT_RESOURCE_TYPES)
        payment_qs = payment_qs.distinct()
        payment_ids = list(payment_qs.values_list("id", flat=True))
        general_qs = AuditLog.objects.exclude(id__in=payment_ids)

        self._report("payment", payment_qs, settings.PAYMENT_LOG_RETENTION_YEARS)
        self._report("general", general_qs, settings.AUDIT_LOG_RETENTION_YEARS)

        if failures:
            for msg in failures:
                self.stderr.write(self.style.ERROR(f"FAIL {msg}"))
            self.stderr.write(self.style.ERROR(
                "Retention floor verification FAILED."
            ))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("Retention floor verification PASSED."))

    def _delete_is_blocked(self):
        """Return True if attempting to DELETE a real audit row raises."""
        row = AuditLog.objects.first()
        if row is None:
            # No rows to test against; the trigger presence check (step 1) still
            # guards the floor. Treat as not-disproven.
            return True
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"DELETE FROM {AUDIT_TABLE} WHERE id = %s", [str(row.id)]
                    )
                # If we get here the DELETE was accepted — roll back and fail.
                transaction.set_rollback(True)
            return False
        except Exception:
            return True

    def _report(self, label, queryset, retention_years):
        count = queryset.count()
        oldest = queryset.order_by("timestamp").values_list(
            "timestamp", flat=True
        ).first()
        newest = queryset.order_by("-timestamp").values_list(
            "timestamp", flat=True
        ).first()
        self.stdout.write(
            f"     {label} logs: count={count} retention>={retention_years}y "
            f"oldest={oldest} newest={newest}"
        )
