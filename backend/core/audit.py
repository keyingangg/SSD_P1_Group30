"""Audit logging helper."""

from .models import AuditLog


def log_action(
    user=None,
    action="",
    resource_type="",
    resource_id=None,
    ip_address=None,
    user_agent="",
    metadata=None,
):
    """Write an append-only audit log entry.

    User-supplied data must be encoded/sanitised before being recorded to
    prevent log injection.
    """
    AuditLog.objects.create(
        user=user,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {},
    )
