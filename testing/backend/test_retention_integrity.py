"""Tests for the retention floor + referential-integrity verifiers."""
from io import StringIO

import pytest
from django.core.management import call_command
from django.db import connection, transaction

from core.audit import log_action
from core.models import AuditLog


@pytest.mark.django_db
def test_raw_delete_on_audit_logs_is_blocked():
    """The append-only trigger must reject a direct DELETE on audit_logs."""
    log_action(user=None, action="TEST_EVENT", resource_type="Test")
    row = AuditLog.objects.first()
    assert row is not None

    with pytest.raises(Exception):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM audit_logs WHERE id = %s", [str(row.id)]
                )

    # Row still present — nothing was deleted.
    assert AuditLog.objects.filter(pk=row.pk).exists()


# Note: retention-command reporting is covered by main's verify_retention_policy
# and its own tests. The append-only floor it relies on is verified directly by
# test_raw_delete_on_audit_logs_is_blocked above.


@pytest.mark.django_db
def test_verify_integrity_finds_expected_fks():
    """verify_integrity exits 0 with all expected FK constraints present."""
    out = StringIO()
    call_command("verify_integrity", stdout=out)
    output = out.getvalue()

    assert "PASSED" in output
    assert "orders.winner_id" in output
