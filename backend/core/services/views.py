"""Read-only audit log views with tiered access control.

Access tiers (NFSR-AC-04 / FSR-AC-05 / FSR-AC-06):
  superuser / senior auditor  → full trail (all actions, including payment logs)
  regular admin (is_staff)    → auction and bid logs only; payment entries hidden

All audit-log reads are themselves logged by RBACMiddleware (FSR-AC-06).
"""
from django.core.paginator import Paginator
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminUser
from .audit import PAYMENT_ACTIONS, PAYMENT_RESOURCE_TYPES
from .models import AuditLog


class AuditLogListView(APIView):
    """Return a paginated, read-only list of audit log entries for staff auditors.

    Regular admins (is_staff only) see auction/bid logs exclusively.
    Superusers and designated auditors see the full audit trail including
    payment events (FSR-AC-05 / FSR-AC-06).
    """

    permission_classes = [IsAdminUser]
    staff_only = True

    def get(self, request):
        queryset = AuditLog.objects.order_by("-timestamp", "-id")

        # Tiered read access: regular admin may not see payment logs.
        if not request.user.is_superuser:
            queryset = queryset.exclude(
                action__in=PAYMENT_ACTIONS
            ).exclude(
                resource_type__in=PAYMENT_RESOURCE_TYPES
            )

        paginator = Paginator(queryset, 20)
        page = paginator.get_page(request.query_params.get("page", 1))

        results = []
        for entry in page.object_list:
            results.append({
                "id": str(entry.id),
                "action": entry.action,
                "resource_type": entry.resource_type,
                "resource_id": str(entry.resource_id) if entry.resource_id else None,
                "user": str(entry.user_id) if entry.user_id else None,
                "role": entry.role,
                "ip_address": entry.ip_address,
                "device_fingerprint": entry.device_fingerprint,
                "request_method": entry.request_method,
                "endpoint_path": entry.endpoint_path,
                "before_data": entry.before_data,
                "after_data": entry.after_data,
                "exception_type": entry.exception_type or None,
                "stack_trace": entry.stack_trace or None,
                "metadata": entry.metadata,
                "row_hash": entry.row_hash,
                "timestamp": entry.timestamp.isoformat(),
            })

        return Response(
            {
                "count": paginator.count,
                "next": page.next_page_number() if page.has_next() else None,
                "previous": page.previous_page_number() if page.has_previous() else None,
                "results": results,
            },
            status=200,
        )
