"""Management command: verify AuditLog row hashes have not been tampered with.

Recomputes the SHA-256 row hash for each AuditLog entry from its own stored
fields and compares it against the hash written at insert time
(NFSR-AC-04 / FSR-IN-09). AuditLog is append-only at the application level
(AuditLog.save() rejects updates), so a mismatch means either the row was
modified via a path that bypassed the ORM (e.g. direct SQL) or the hashing
logic itself changed incompatibly.

Rows anonymised via accounts.anonymisation.anonymise_user_data are expected
to fail recomputation — their row_hash is intentionally overwritten with the
"[PII_ANONYMISED]" marker rather than a real hash — and are skipped.

Known limitation: Django's GenericIPAddressField can normalise IPv6 address
formatting on save, which could make a legitimate row's stored ip_address
differ from the exact string used in the original hash computation. This
would surface as a false-positive mismatch for IPv6-sourced entries only.

Run on a schedule (e.g. daily cron):
    python manage.py verify_audit_log_hashes
    python manage.py verify_audit_log_hashes --verbose
"""
from django.core.management.base import BaseCommand

from core.cross_cutting.alerts import send_security_alert
from core.cross_cutting.audit import _compute_row_hash
from core.data.models import AuditLog

ANONYMISED_MARKER = "[PII_ANONYMISED]"


def _rebuild_payload(row):
    """Reconstruct the exact payload shape log_action() hashed at write time."""
    return {
        "user_id": str(row.user_id) if row.user_id else None,
        "action": row.action,
        "resource_type": row.resource_type,
        "resource_id": str(row.resource_id) if row.resource_id else None,
        "ip_address": row.ip_address,
        "user_agent": row.user_agent,
        "device_fingerprint": row.device_fingerprint,
        "role": row.role,
        "before": row.before_data,
        "after": row.after_data,
        "exception_type": row.exception_type,
        "stack_trace": row.stack_trace,
        "request_method": row.request_method,
        "endpoint_path": row.endpoint_path,
        "metadata": row.metadata,
        "timestamp": row.timestamp.isoformat(),
    }


class Command(BaseCommand):
    help = "Recompute and verify AuditLog row hashes; report any mismatch (NFSR-AC-04)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="List every row checked, not just mismatches.",
        )

    def handle(self, *args, **options):
        verbose = options["verbose"]

        checked = 0
        skipped = 0
        mismatches = []

        for row in AuditLog.objects.iterator():
            if row.row_hash == ANONYMISED_MARKER:
                skipped += 1
                continue

            checked += 1
            recomputed = _compute_row_hash(_rebuild_payload(row))
            if recomputed != row.row_hash:
                mismatches.append(row)
                self.stderr.write(
                    f"  MISMATCH id={row.id} action={row.action} timestamp={row.timestamp}"
                )
                try:
                    send_security_alert(
                        subject="Audit log hash mismatch detected",
                        message=(
                            f"AuditLog row {row.id} (action={row.action}, "
                            f"timestamp={row.timestamp.isoformat()}) failed SHA-256 "
                            "hash verification. This indicates tampering or an "
                            "out-of-band write bypassing the append-only ORM path."
                        ),
                        severity="critical",
                        metadata={
                            "row_id": str(row.id),
                            "action": row.action,
                            "resource_type": row.resource_type,
                            "timestamp": row.timestamp.isoformat(),
                            "stored_hash": row.row_hash,
                            "recomputed_hash": recomputed,
                        },
                    )
                except Exception:
                    self.stderr.write(f"  Failed to send security alert for row {row.id}")
            elif verbose:
                self.stdout.write(f"  OK id={row.id} action={row.action}")

        self.stdout.write(
            f"Checked {checked} row(s), skipped {skipped} anonymised row(s), "
            f"{len(mismatches)} mismatch(es)."
        )

        if mismatches:
            self.stdout.write(
                self.style.ERROR(
                    f"{len(mismatches)} audit log row(s) failed hash verification — "
                    "possible tampering or an out-of-band write."
                )
            )
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("All audit log rows verified."))
