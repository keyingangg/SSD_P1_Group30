"""Verify referential-integrity FK constraints exist in the live database.

Introspects the running schema and asserts a real foreign-key constraint backs
each cross-table relationship that must survive at the DB level, then prints the
on_delete matrix. Exits non-zero if any expected constraint is missing.

audit_logs.user is intentionally db_constraint=False (audit rows must survive
user deletion), so this command asserts that FK is ABSENT. See
docs/DATA_INTEGRITY.md.

    python manage.py verify_integrity
"""
from django.core.management.base import BaseCommand
from django.db import connection

# (table, column) -> human-readable on_delete for the matrix printout.
EXPECTED_FKS = {
    ("bids", "listing_id"): "CASCADE",
    ("bids", "bidder_id"): "SET_NULL",
    ("orders", "winner_id"): "SET_NULL",
    ("orders", "winning_bid_id"): "PROTECT",
    ("orders", "listing_id"): "PROTECT",
}

# FKs that must NOT have a DB constraint (deliberately db_constraint=False).
EXPECTED_ABSENT_FKS = {
    ("audit_logs", "user_id"): "DO_NOTHING (db_constraint=False)",
}


class Command(BaseCommand):
    help = "Verify cross-table foreign-key constraints exist in the database."

    def handle(self, *args, **options):
        failures = []
        introspection = connection.introspection

        self.stdout.write("on_delete / FK constraint matrix:")

        with connection.cursor() as cursor:
            for (table, column), on_delete in EXPECTED_FKS.items():
                has_fk = self._has_fk(introspection, cursor, table, column)
                status = self.style.SUCCESS("OK  ") if has_fk else self.style.ERROR("FAIL")
                self.stdout.write(
                    f"  {status} {table}.{column:<16} on_delete={on_delete:<9} "
                    f"db_constraint={'yes' if has_fk else 'MISSING'}"
                )
                if not has_fk:
                    failures.append(f"FK constraint missing: {table}.{column}")

            for (table, column), note in EXPECTED_ABSENT_FKS.items():
                has_fk = self._has_fk(introspection, cursor, table, column)
                status = self.style.SUCCESS("OK  ") if not has_fk else self.style.ERROR("FAIL")
                self.stdout.write(
                    f"  {status} {table}.{column:<16} {note} "
                    f"db_constraint={'UNEXPECTED' if has_fk else 'absent (intended)'}"
                )
                if has_fk:
                    failures.append(
                        f"FK constraint unexpectedly present: {table}.{column}"
                    )

        if failures:
            for msg in failures:
                self.stderr.write(self.style.ERROR(msg))
            self.stderr.write(self.style.ERROR("Integrity verification FAILED."))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("Integrity verification PASSED."))

    @staticmethod
    def _has_fk(introspection, cursor, table, column):
        constraints = introspection.get_constraints(cursor, table)
        for details in constraints.values():
            if details.get("foreign_key") and column in details.get("columns", []):
                return True
        return False
