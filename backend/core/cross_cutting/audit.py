"""Audit logging helper.

Provides a single append-only API for structured audit entries with masking,
encoding, per-row hashing, and consistent role derivation.

Requirements covered:
  NFSR-AC-01  Every entry attributed to the acting user.
  NFSR-AC-03  Entry includes: user ID, role, action type, UTC timestamp,
              source IP, device fingerprint; data-modifying entries include
              before/after values; exception entries include exception type,
              stack trace, request method, endpoint path.
  NFSR-AC-03  Sensitive data (passwords, tokens, card data) masked.
  NFR-06      User-supplied data escaped before writing to log.
  NFSR-IN-07  SHA-256 hash of all other columns appended at insert time.
"""
from html import escape as _escape
import hashlib
import json
import traceback as _traceback

from django.utils import timezone

from ..data.models import AuditLog


SENSITIVE_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "card_number",
    "cvv",
    "card_cvc",
    "ssn",
    "secret",
    "otp_code",
    "otp",
}

# Payment-log actions: read access restricted to senior admin / auditor.
PAYMENT_ACTIONS = frozenset({
    "ORDER_PAID",
    "ORDER_FULFILLMENT_UPDATED",
    "ORDER_ACCESS_DENIED",
    "CHECKOUT_ACCESS_DENIED",
    "CHECKOUT_INITIATED",
    "PAYMENT_WINNER_MISMATCH",
    "PAYMENT_CONFIRM_MISMATCH",
})
PAYMENT_RESOURCE_TYPES = frozenset({"Order"})


def _mask_value(key, value):
    if value is None:
        return None
    if key.lower() in SENSITIVE_KEYS:
        return "[MASKED]"
    # Crude masking for bare PAN-like digit strings (≥ 12 digits).
    if isinstance(value, str) and value.isdigit() and len(value) >= 12:
        return value[:4] + "-" + "*" * (len(value) - 8) + "-" + value[-4:]
    return value


def _sanitize_dict(d):
    """Recursively mask sensitive keys and HTML-escape all string values."""
    if d is None:
        return None
    out = {}
    for k, v in d.items():
        try:
            if isinstance(v, dict):
                out[k] = _sanitize_dict(v)
            else:
                out[k] = _escape(str(_mask_value(k, v)))
        except Exception:
            out[k] = "[UNSERIALIZABLE]"
    return out


def _derive_role(user, explicit_role=None):
    """Return a role string for the acting user.

    Priority: explicit_role > user.role attr > is_superuser > is_staff > "user"
    Falls back to "anonymous" for unauthenticated or None.
    """
    if explicit_role:
        return explicit_role
    if user is None or not getattr(user, "is_authenticated", False):
        return "anonymous"
    role_attr = getattr(user, "role", None)
    if role_attr:
        return str(role_attr)
    if getattr(user, "is_superuser", False):
        return "superuser"
    if getattr(user, "is_staff", False):
        return "staff"
    return "user"


def device_fingerprint(ip: str, user_agent: str) -> str:
    """Derive a pseudonymous device/browser fingerprint from IP + UA."""
    raw = f"{ip or ''}:{user_agent or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _compute_row_hash(payload: dict) -> str:
    """SHA-256 over a deterministic JSON encoding of the payload."""
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _format_stack(exc: Exception) -> str:
    """Format an exception's own traceback (not sys.exc_info())."""
    return "".join(
        _traceback.format_exception(type(exc), exc, exc.__traceback__)
    )


def log_action(
    user=None,
    action: str = "",
    resource_type: str = "",
    resource_id=None,
    ip_address=None,
    user_agent: str = "",
    device_fingerprint: str = "",
    role: str = "",
    before=None,
    after=None,
    exception: Exception | None = None,
    request_method: str = "",
    endpoint_path: str = "",
    metadata: dict | None = None,
):
    """Create an append-only AuditLog entry.

    Guarantees:
    - Passwords, tokens, card data masked before storage (NFSR-AC-03).
    - All string values HTML-escaped to prevent log injection (NFR-06).
    - SHA-256 row hash computed over canonical payload and stored (NFSR-IN-07).
    - User ID and role-at-time-of-action always recorded (NFSR-AC-01/03).
    - Exception entries include type and full stack trace (NFSR-AC-03).
    - Timestamp passed explicitly so the hashed value equals the stored value.
    """
    ts = timezone.now()

    derived_role = _escape(_derive_role(user, role))
    safe_before = _sanitize_dict(before) if before else None
    safe_after = _sanitize_dict(after) if after else None
    safe_metadata = _sanitize_dict(metadata) if metadata else {}

    # Escape all user-influenced string fields once so the same value is used
    # for both the row-hash payload and the DB write (NFR-06 / NFSR-IN-07).
    escaped_action = _escape(action or "")
    escaped_resource_type = _escape(resource_type or "")
    escaped_user_agent = _escape(user_agent or "")
    escaped_device_fingerprint = _escape(device_fingerprint or "")
    escaped_request_method = _escape(request_method or "")
    escaped_endpoint_path = _escape(endpoint_path or "")

    exc_type = type(exception).__name__ if exception else ""
    stack_trace = _format_stack(exception) if exception else ""

    payload = {
        "user_id": str(user.id) if getattr(user, "id", None) else None,
        "action": escaped_action,
        "resource_type": escaped_resource_type,
        "resource_id": str(resource_id) if resource_id else None,
        "ip_address": ip_address,
        "user_agent": escaped_user_agent,
        "device_fingerprint": escaped_device_fingerprint,
        "role": derived_role,
        "before": safe_before,
        "after": safe_after,
        "exception_type": exc_type,
        "stack_trace": stack_trace,
        "request_method": escaped_request_method,
        "endpoint_path": escaped_endpoint_path,
        "metadata": safe_metadata,
        "timestamp": ts.isoformat(),
    }

    row_hash = _compute_row_hash(payload)

    AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=escaped_action,
        resource_type=escaped_resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=escaped_user_agent,
        role=derived_role,
        device_fingerprint=escaped_device_fingerprint,
        before_data=safe_before,
        after_data=safe_after,
        exception_type=exc_type,
        stack_trace=stack_trace,
        request_method=escaped_request_method,
        endpoint_path=escaped_endpoint_path,
        metadata=safe_metadata,
        row_hash=row_hash,
        timestamp=ts,
    )
