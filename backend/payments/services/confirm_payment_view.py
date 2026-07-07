"""Direct payment-confirmation API (diagram: svc_confirm_payment)."""
import logging

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.services.permissions import IsEmailVerified
from accounts.business.session_manager import get_client_ip

from ..business.order_service import OrderService, OrderServiceError
from ..data.models import Order

logger = logging.getLogger("securebid")


class ConfirmPaymentView(APIView):
    """Directly confirm payment by verifying the PaymentIntent with Stripe's API.

    Called by the frontend immediately after stripe.confirmPayment() succeeds.
    Eliminates the need for the Stripe CLI / webhook listener in development.
    The webhook remains as a safety net for edge cases (browser crash, etc.).
    """

    permission_classes = [IsEmailVerified]

    def post(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id)

        if order.winner_id != request.user.id:
            logger.warning(
                "ConfirmPayment access denied user=%s order=%s ip=%s",
                request.user.email, order_id, get_client_ip(request),
            )
            return Response({"detail": "Forbidden."}, status=403)

        payment_intent_id = request.data.get("payment_intent_id", "").strip()

        try:
            already_confirmed = OrderService.confirm_payment(
                order,
                request.user,
                payment_intent_id,
                client_ip=get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                session_key=request.session.session_key,
            )
        except OrderServiceError as exc:
            return Response({"detail": exc.detail}, status=exc.status_code)

        if already_confirmed:
            return Response({"detail": "Payment already confirmed."}, status=200)
        return Response({"detail": "Payment confirmed."}, status=200)
