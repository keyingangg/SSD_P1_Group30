"""Admin audit log read API (diagram: svc_auditlog)."""
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from core.cross_cutting.audit import log_action, device_fingerprint as _device_fingerprint

from ..business.session_manager import get_client_ip
from .permissions import IsAdminUser

_ACTION_LABEL_MAP = {
    "login_success": "Login successful",
    "login_failed": "Login failed",
    "logout": "Logged out",
    "mfa_login_success": "MFA login successful",
    "mfa_login_failed": "MFA login failed",
    "mfa_enrolled": "MFA enrolled",
    "mfa_disabled": "MFA disabled",
    "bid_placed": "Bid placed",
    "bid_rejected": "Bid rejected",
    "admin_account_toggled": "Account locked/unlocked",
    "admin_account_deleted": "Account deleted",
    "admin_listing_status_changed": "Listing status changed",
    "admin_listing_deleted": "Listing deleted",
    "ORDER_PAID": "Payment received",
    "ORDER_FULFILLMENT_UPDATED": "Fulfillment updated",
    "ORDER_ACCESS_DENIED": "Order access denied",
    "CHECKOUT_ACCESS_DENIED": "Checkout access denied",
    "CHECKOUT_INITIATED": "Checkout initiated",
    "PAYMENT_WINNER_MISMATCH": "Payment winner mismatch",
    "PAYMENT_CONFIRM_MISMATCH": "Payment confirm mismatch",
}

_CATEGORY_FILTERS = {
    "login_logout": lambda qs: qs.filter(
        action__in=["login_success", "login_failed", "logout",
                    "mfa_login_success", "mfa_login_failed",
                    "mfa_enrolled", "mfa_disabled"]
    ),
    "bids": lambda qs: qs.filter(action__icontains="bid"),
    "admin_actions": lambda qs: qs.filter(action__istartswith="admin_"),
    "payments": lambda qs: qs.filter(
        action__in=["ORDER_PAID", "ORDER_FULFILLMENT_UPDATED",
                    "ORDER_ACCESS_DENIED", "CHECKOUT_ACCESS_DENIED",
                    "CHECKOUT_INITIATED", "PAYMENT_WINNER_MISMATCH",
                    "PAYMENT_CONFIRM_MISMATCH"]
    ) | qs.filter(resource_type="Order"),
    "errors": lambda qs: qs.exclude(exception_type=""),
}

# Categories a regular admin (non-superuser) may request.
_REGULAR_ADMIN_CATEGORIES = {"all", "bids"}


# For the "all" tab, regular admins only see auction + bid events.
def _restrict_to_auction_and_bids(qs):
    return qs.filter(
        Q(action__icontains="bid") | Q(action__icontains="listing")
    )


def _severity(entry):
    action = entry.action.lower()
    if entry.exception_type or "denied" in action or "error" in action:
        return "error"
    if "failed" in action or "rejected" in action or "mismatch" in action:
        return "warning"
    if entry.role in ("staff", "superuser", "admin") or action.startswith("admin_"):
        return "admin"
    return "success"


def _serialize_entry(entry):
    user = entry.user
    if user is not None:
        try:
            user_display = user.email
            is_admin = user.is_staff or user.is_superuser
        except Exception:
            user_display = "—"
            is_admin = False
    else:
        user_display = "System"
        is_admin = False

    action_label = _ACTION_LABEL_MAP.get(entry.action, entry.action.replace("_", " ").title())
    device = entry.device_fingerprint[:12] if entry.device_fingerprint else "—"

    ref = ""
    if entry.resource_type:
        ref = entry.resource_type
        if entry.resource_id:
            ref += f" {str(entry.resource_id)[:8]}"

    return {
        "timestamp": entry.timestamp.isoformat(),
        "user_display": user_display,
        "is_admin": is_admin,
        "action_label": action_label,
        "ip_address": entry.ip_address or "—",
        "device": device,
        "ref": ref or "—",
        "severity": _severity(entry),
    }


class AdminAuditLogView(APIView):
    """Return audit log entries for the admin panel (staff only).

    Access tiers (NFSR-AC-04 / FSR-AC-06):
    - Superuser: full trail, all categories including payments.
    - Regular admin: auction and bid logs only; payment/login/error
      categories are blocked with 403.
    Every read is itself logged (NFSR-AC-04).
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        from core.data.models import AuditLog

        is_superuser = request.user.is_superuser
        category = request.query_params.get("category", "all")
        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")

        # Enforce category-level access for regular admins.
        if not is_superuser and category not in _REGULAR_ADMIN_CATEGORIES:
            log_action(
                user=request.user,
                action="audit_log_access_denied",
                resource_type="AuditLog",
                ip_address=ip,
                user_agent=ua,
                device_fingerprint=_device_fingerprint(ip, ua),
                role="staff",
                request_method=request.method,
                endpoint_path=request.path,
                metadata={"category": category, "reason": "insufficient_role"},
            )
            return Response(
                {"detail": "You do not have permission to view this category."},
                status=403,
            )

        qs = AuditLog.objects.select_related("user").order_by("-timestamp")

        # Regular admins: restrict "all" to auction + bid events.
        if not is_superuser and category == "all":
            qs = _restrict_to_auction_and_bids(qs)
        else:
            filter_fn = _CATEGORY_FILTERS.get(category)
            if filter_fn:
                qs = filter_fn(qs)

        results = [_serialize_entry(e) for e in qs[:500]]

        # Log this read access (NFSR-AC-04).
        try:
            log_action(
                user=request.user,
                action="audit_log_read",
                resource_type="AuditLog",
                ip_address=ip,
                user_agent=ua,
                device_fingerprint=_device_fingerprint(ip, ua),
                role="superuser" if is_superuser else "staff",
                request_method=request.method,
                endpoint_path=request.path,
                metadata={"category": category, "result_count": len(results)},
            )
        except Exception:
            pass

        return Response(results)
