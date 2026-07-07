"""Order detail read API (diagram: svc_order_detail)."""
import logging

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.services.permissions import IsEmailVerified
from accounts.business.session_manager import get_client_ip
from core.cross_cutting.audit import log_action

from ..business.order_service import OrderAccessDenied, OrderService
from ..data.models import Order

logger = logging.getLogger("securebid")


class OrderDetailView(APIView):
    """Read a single order (scoped to the winner or an admin)."""

    permission_classes = [IsEmailVerified]

    def get(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id)
        try:
            OrderService.assert_can_access_order(order, request.user)
        except OrderAccessDenied:
            logger.warning(
                "Order access denied for user=%s order=%s ip=%s agent=%s",
                request.user.email,
                order_id,
                get_client_ip(request),
                request.META.get("HTTP_USER_AGENT", ""),
            )
            log_action(
                user=request.user,
                action="ORDER_ACCESS_DENIED",
                resource_type="Order",
                resource_id=order.id,
                ip_address=get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                metadata={
                    "requested_by": str(request.user.id),
                    "session_id": request.session.session_key,
                    "listing_id": str(order.winning_bid.listing_id),
                },
            )
            return Response({"detail": "Forbidden."}, status=403)

        return Response(OrderService.get_detail(order), status=200)
