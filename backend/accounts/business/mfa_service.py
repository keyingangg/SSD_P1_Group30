"""MFA Service — TOTP enrolment/verification helpers (diagram: biz_mfa)."""
from core.cross_cutting.audit import log_action, device_fingerprint as _device_fingerprint

from .session_manager import get_client_ip


def log_mfa_event(user, action_name, request):
    """Write a structured audit log entry for MFA enrolment/disablement (NFSR-AC-02)."""
    ip = get_client_ip(request)
    ua = request.META.get("HTTP_USER_AGENT", "") if request else ""
    log_action(
        user=user,
        action=action_name,
        resource_type="User",
        resource_id=user.id,
        ip_address=ip,
        user_agent=ua,
        device_fingerprint=_device_fingerprint(ip, ua),
        role="staff" if getattr(user, "is_staff", False) else "user",
        request_method=getattr(request, "method", ""),
        endpoint_path=getattr(request, "path", ""),
    )
