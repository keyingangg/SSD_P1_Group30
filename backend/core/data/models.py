"""Cross-cutting models for SecureBid (audit log)."""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """Append-only record of a security-relevant or auction-critical event."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=100, blank=True)
    resource_id = models.UUIDField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    role = models.CharField(max_length=100, blank=True)
    device_fingerprint = models.CharField(max_length=255, blank=True)
    before_data = models.JSONField(null=True, blank=True)
    after_data = models.JSONField(null=True, blank=True)
    exception_type = models.CharField(max_length=255, blank=True)
    stack_trace = models.TextField(blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    endpoint_path = models.CharField(max_length=255, blank=True)
    row_hash = models.CharField(max_length=64, editable=False)
    metadata = models.JSONField(null=True, blank=True)
    # editable=False + explicit default (not auto_now_add) so log_action() can
    # pass the exact timestamp used for the SHA-256 row hash computation and
    # have that value stored verbatim.  auto_now_add calls timezone.now()
    # inside pre_save(), overwriting the caller-supplied value.
    timestamp = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "audit_logs"
        default_permissions = ("add", "view")
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action} @ {self.timestamp}"

    def save(self, *args, **kwargs):
        # Enforce append-only at application level: no updates allowed.
        if self._state.adding is False:
            raise RuntimeError("AuditLog entries are append-only and may not be modified")
        super().save(*args, **kwargs)
