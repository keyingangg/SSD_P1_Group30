import axiosClient from "./axiosClient.js";

export async function confirmPaymentIntent(orderId, paymentIntentId) {
  const { data } = await axiosClient.post(`/payments/orders/${orderId}/confirm/`, {
    payment_intent_id: paymentIntentId,
  });
  return data;
}

export async function getAdminOrders() {
  const { data } = await axiosClient.get("/payments/orders/");
  return data;
}

export async function updateFulfillmentStatus(orderId, fulfillmentStatus) {
  const { data } = await axiosClient.patch(`/payments/orders/${orderId}/fulfillment/`, {
    fulfillment_status: fulfillmentStatus,
  });
  return data;
}

// Fetch an order's details (winner or admin only, server-enforced).
export async function getOrderDetail(orderId) {
  const { data } = await axiosClient.get(`/payments/orders/${orderId}/`);
  return data;
}

// Create a Stripe PaymentIntent for an order. Returns client_secret,
// publishable_key, amount, currency, and a `demo` flag (true when no Stripe
// keys are configured on the backend).
export async function createPaymentIntent(orderId, deliveryAddress) {
  const payload = { order_id: orderId };
  if (deliveryAddress) payload.delivery_address = deliveryAddress;
  const { data } = await axiosClient.post("/payments/create-intent/", payload);
  return data;
}
