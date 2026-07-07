"""Admin order list API (diagram: svc_admin_order_list)."""
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.services.permissions import IsAdminUser

from ..business.order_service import OrderService


class AdminOrderListView(APIView):
    """List all orders for admin review — admin/staff only (FR-10, FR-11)."""

    permission_classes = [IsAdminUser]
    staff_only = True

    def get(self, request):
        return Response(OrderService.list_for_admin(), status=200)
