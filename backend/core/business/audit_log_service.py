"""Audit Log Service (diagram: business-layer box, Admin frame).

Thin facade over the Cross-Cutting audit logging primitives so the Business
Layer exposes a named service for recording audit entries, while the masking,
escaping, and row-hashing implementation stays in cross_cutting/audit.py where
it is shared by both the User and Admin frames.
"""
from core.cross_cutting.audit import (  # noqa: F401
    device_fingerprint,
    log_action,
)
