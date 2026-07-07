"""Order-fulfilment update API (diagram: svc_update_fulfillment)."""
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.services.permissions import IsAdminUser
from accounts.business.session_manager import get_client_ip

from ..business.order_fulfilment_service import OrderFulfilmentService
from ..business.order_service import OrderServiceError
from ..data.models import Order
from .serializers import UpdateFulfillmentSerializer


class UpdateFulfillmentView(APIView):
    """Update an order's fulfilment status (admin only), forward-only."""

    permission_classes = [IsAdminUser]
    staff_only = True

    def patch(self, request, order_id):
        serializer = UpdateFulfillmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["fulfillment_status"]

        order = get_object_or_404(Order, pk=order_id)

        try:
            OrderFulfilmentService.update_status(
                order,
                new_status,
                user=request.user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                session_key=request.session.session_key,
            )
        except OrderServiceError as exc:
            return Response({"detail": exc.detail}, status=exc.status_code)

        return Response({"detail": "Order fulfillment updated."}, status=200)
