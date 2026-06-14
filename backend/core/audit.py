"""Audit logging helper."""


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
    # TODO: create AuditLog row; later add SHA-256 entry hashing for
    # tamper-evidence.
    pass
