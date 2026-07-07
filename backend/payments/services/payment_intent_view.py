"""Create-PaymentIntent API (diagram: svc_create_payment_intent)."""
import logging

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.services.permissions import IsEmailVerified
from accounts.business.session_manager import get_client_ip

from ..business.order_service import OrderAccessDenied, OrderService, OrderServiceError
from ..data.models import Order
from .serializers import CreatePaymentIntentSerializer

logger = logging.getLogger("securebid")


class CreatePaymentIntentView(APIView):
    """Create a Stripe PaymentIntent for the authenticated auction winner."""

    permission_classes = [IsEmailVerified]

    def post(self, request):
        serializer = CreatePaymentIntentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order_id = serializer.validated_data["order_id"]
        delivery_address = serializer.validated_data.get("delivery_address", "")

        order = get_object_or_404(Order, pk=order_id)

        try:
            result = OrderService.initiate_checkout(
                order,
                request.user,
                delivery_address,
                client_ip=get_client_ip(request),
                remote_addr=request.META.get("REMOTE_ADDR", ""),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                session_key=request.session.session_key,
            )
        except OrderAccessDenied:
            logger.warning(
                "Checkout access denied for user=%s order=%s ip=%s",
                request.user.email,
                order_id,
                get_client_ip(request),
            )
            return Response({"detail": "Forbidden."}, status=403)
        except OrderServiceError as exc:
            return Response({"detail": exc.detail}, status=exc.status_code)

        return Response(result, status=200)
