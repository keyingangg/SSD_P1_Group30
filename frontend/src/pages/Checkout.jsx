import { useParams } from "react-router-dom";
import { loadStripe } from "@stripe/stripe-js";
import { Elements } from "@stripe/react-stripe-js";

// DEMO MODE: Uses Stripe test publishable key and mock payment intent.
// Stripe Elements UI renders normally. Use Stripe test card 4242 4242 4242 4242
// with any future expiry and any CVC to simulate a successful payment.
// No real charges will occur.
const stripePromise = loadStripe("pk_test_placeholder");

// Checkout page for the auction winner.
export default function Checkout() {
  const { orderId } = useParams();

  // TODO: fetch order detail and create a (mock) payment intent for orderId.
  return (
    <main>
      <h1>Checkout</h1>
      <Elements stripe={stripePromise}>
        {/* TODO: Stripe Elements card form + pay button */}
      </Elements>
    </main>
  );
}
