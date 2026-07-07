"""Business logic for forward-only order fulfilment-status transitions (FR-10)."""
from core.cross_cutting.audit import log_action

from ..data.models import Order
from .order_service import OrderServiceError

# An order may only advance to the single next state — never skip ahead or
# move backwards. pending_payment -> paid is driven by the Stripe webhook, not
# this transition table.
FULFILLMENT_TRANSITIONS = {
    "paid": "processing",
    "processing": "shipped",
    "shipped": "delivered",
}


class OrderFulfilmentService:
    """Validates and applies admin-driven fulfilment-status transitions."""

    @staticmethod
    def next_allowed_status(current_status):
        return FULFILLMENT_TRANSITIONS.get(current_status)

    @classmethod
    def update_status(cls, order, new_status, *, user, ip_address, user_agent, session_key):
        """Validate and apply a forward-only fulfilment transition, then audit-log it."""
        if new_status not in dict(Order.FULFILLMENT_CHOICES):
            raise OrderServiceError("Invalid fulfillment status.", status_code=400)

        allowed_next = cls.next_allowed_status(order.fulfillment_status)
        if new_status != allowed_next:
            detail = (
                f"Cannot move order from '{order.fulfillment_status}' to "
                f"'{new_status}'. "
                + (
                    f"The next allowed status is '{allowed_next}'."
                    if allowed_next
                    else "This order can no longer be advanced."
                )
            )
            raise OrderServiceError(detail, status_code=400)

        order.fulfillment_status = new_status
        order.save(update_fields=["fulfillment_status", "updated_at"])
        log_action(
            user=user,
            action="ORDER_FULFILLMENT_UPDATED",
            resource_type="Order",
            resource_id=order.id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "fulfillment_status": new_status,
                "session_id": session_key,
                "listing_id": str(order.winning_bid.listing_id),
            },
        )
