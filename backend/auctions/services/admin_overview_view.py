"""Admin dashboard overview API (diagram: svc_admin_overview)."""
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.services.permissions import IsAdminUser

from ..business.listing_management_service import get_active_listings_summary


class AdminOverviewView(APIView):
    """Return summary stats for the admin dashboard (staff only)."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        from django.contrib.auth import get_user_model
        from core.data.models import AuditLog
        from payments.models import Order

        User = get_user_model()
        now = timezone.now()

        active_listing_count, bids_today, active_auction_data = get_active_listings_summary(now)
        pending_payment_count = Order.objects.filter(fulfillment_status="pending_payment").count()

        registered_users = User.objects.filter(is_anonymised=False).count()

        recent_audit = (
            AuditLog.objects.select_related("user")
            .order_by("-timestamp")[:10]
        )

        _label_map = {
            "login_success": "Login successful",
            "login_failed": "Login failed",
            "logout": "Logged out",
            "mfa_login_success": "MFA login successful",
            "mfa_login_failed": "MFA login failed",
            "bid_placed": "Bid placed",
            "bid_rejected": "Bid rejected",
            "admin_account_toggled": "Account locked/unlocked",
            "admin_account_deleted": "Account deleted",
            "admin_listing_status_changed": "Listing status changed",
        }

        audit_events = []
        for e in recent_audit:
            actor = e.user.email if e.user else "System"
            is_admin = (e.user.is_staff or e.user.is_superuser) if e.user else False
            label = _label_map.get(e.action, e.action.replace("_", " ").title())
            audit_events.append({
                "actor": actor,
                "action": label,
                "timestamp": e.timestamp.isoformat(),
                "is_admin": is_admin,
            })

        return Response({
            "stats": {
                "active_listings": active_listing_count,
                "pending_payments": pending_payment_count,
                "bids_today": bids_today,
                "registered_users": registered_users,
            },
            "audit_events": audit_events,
            "active_auctions": active_auction_data,
            "pending_orders_count": pending_payment_count,
        })
