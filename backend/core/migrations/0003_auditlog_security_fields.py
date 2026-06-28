"""
Add security-required fields to AuditLog and harden the timestamp so the
SHA-256 row hash is computed on the exact value that is stored.

Fields added (all absent from the initial migration):
  role, device_fingerprint, before_data, after_data, exception_type,
  stack_trace, request_method, endpoint_path, row_hash

timestamp is changed from auto_now_add (which always overwrites the caller-
supplied value via pre_save) to an explicit default so log_action() can pass
the value used for the hash and have it stored verbatim.

Meta.default_permissions is narrowed to ("add", "view") to prevent Django
admin from offering "delete" and "change" actions on AuditLog entries.
"""
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_audit_constraints"),
    ]

    operations = [
        # ── New columns ────────────────────────────────────────────────────
        migrations.AddField(
            model_name="auditlog",
            name="role",
            field=models.CharField(max_length=100, blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="auditlog",
            name="device_fingerprint",
            field=models.CharField(max_length=255, blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="auditlog",
            name="before_data",
            field=models.JSONField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="after_data",
            field=models.JSONField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="exception_type",
            field=models.CharField(max_length=255, blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="auditlog",
            name="stack_trace",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="auditlog",
            name="request_method",
            field=models.CharField(max_length=10, blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="auditlog",
            name="endpoint_path",
            field=models.CharField(max_length=255, blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="auditlog",
            name="row_hash",
            field=models.CharField(max_length=64, editable=False, default=""),
            preserve_default=False,
        ),
        # ── Timestamp: switch from auto_now_add to explicit default ────────
        # auto_now_add calls now() inside pre_save(), overriding the value the
        # caller passes to create().  The row hash is computed on the caller's
        # ts value BEFORE create() is called, so there can be a sub-microsecond
        # discrepancy between the hashed timestamp and the stored one.
        # Using editable=False + default=timezone.now preserves the caller-
        # supplied value and keeps the hash consistent with what is stored.
        migrations.AlterField(
            model_name="auditlog",
            name="timestamp",
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                editable=False,
            ),
        ),
        # ── Meta options ────────────────────────────────────────────────────
        migrations.AlterModelOptions(
            name="auditlog",
            options={
                "db_table": "audit_logs",
                "default_permissions": ("add", "view"),
            },
        ),
    ]
