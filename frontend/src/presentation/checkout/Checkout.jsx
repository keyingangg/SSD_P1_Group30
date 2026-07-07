import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { loadStripe } from "@stripe/stripe-js";
import {
  Elements,
  PaymentElement,
  useStripe,
  useElements,
} from "@stripe/react-stripe-js";

import { getOrderDetail, createPaymentIntent, confirmPaymentIntent } from "../../api/payments.js";

function formatMoney(cents, currency) {
  const value = Number(cents) / 100;
  if (Number.isNaN(value)) return "-";
  const code = (currency || "sgd").toUpperCase();
  const prefix = code === "SGD" ? "S$" : `${code} `;
  return `${prefix}${value.toLocaleString("en-SG", { minimumFractionDigits: 0 })}`;
}

function formatDate(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleDateString("en-SG", { day: "numeric", month: "short", year: "numeric" });
}

const TRUST_BADGES = ["SSL", "PCI DSS", "Stripe Verified", "Instant Transfer"];

function PaymentForm({ amountLabel, orderId, onPaid }) {
  const stripe = useStripe();
  const elements = useElements();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!stripe || !elements) return;
    setSubmitting(true);
    setError("");

    const { error: stripeError, paymentIntent } = await stripe.confirmPayment({
      elements,
      redirect: "if_required",
    });

    if (stripeError) {
      setError(stripeError.message || "Payment could not be completed.");
      setSubmitting(false);
      return;
    }

    if (paymentIntent?.status === "succeeded") {
      // Confirm with backend directly so the DB is updated without needing
      // the Stripe CLI webhook listener running locally.
      try {
        await confirmPaymentIntent(orderId, paymentIntent.id);
      } catch (err) {
        console.error("Direct confirm failed:", err?.response?.status, err?.response?.data);
      }
      onPaid();
    } else {
      setError("Payment did not complete. Please try again.");
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <PaymentElement />
      {error && (
        <p className="form-error" style={{ marginTop: "1rem" }}>{error}</p>
      )}
      <button
        type="submit"
        disabled={!stripe || submitting}
        style={{
          marginTop: "1.25rem",
          width: "100%",
          padding: "15px 16px",
          background: "var(--gold)",
          color: "#fff",
          border: "none",
          borderRadius: "var(--radius)",
          fontSize: "15px",
          fontWeight: 700,
          letterSpacing: "0.02em",
          cursor: submitting ? "not-allowed" : "pointer",
          opacity: submitting ? 0.7 : 1,
          transition: "background 0.15s",
        }}
      >
        {submitting ? "Processing…" : `Pay ${amountLabel} Securely`}
      </button>

      <p style={{ fontSize: "11px", color: "var(--muted)", textAlign: "center", marginTop: "0.75rem" }}>
        By completing payment you agree to our Terms of Service · All bids are binding
      </p>

      <div style={{ display: "flex", justifyContent: "center", gap: "1.25rem", marginTop: "1rem", flexWrap: "wrap" }}>
        {TRUST_BADGES.map((b) => (
          <span
            key={b}
            style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted)", display: "flex", alignItems: "center", gap: "4px" }}
          >
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--gold)", display: "inline-block" }} />
            {b}
          </span>
        ))}
      </div>
    </form>
  );
}

function CheckoutSuccess({ order, amountLabel, orderRef }) {
  return (
    <main style={{ maxWidth: 560, margin: "5rem auto", padding: "0 1.5rem", textAlign: "center" }}>
      <div
        style={{
          width: 72, height: 72, borderRadius: "50%",
          background: "rgba(79,157,105,0.1)",
          border: "2px solid rgba(79,157,105,0.35)",
          margin: "0 auto 1.5rem",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}
      >
        <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#4f9d69" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>

      <p className="eyebrow">Payment Confirmed</p>
      <h1 style={{ fontFamily: "var(--font-serif)", fontSize: "2rem", margin: "0.5rem 0 0.5rem" }}>
        Acquisition Complete
      </h1>
      {order?.listing_title && (
        <p style={{ fontSize: "14px", color: "var(--gold-dark)", fontWeight: 600, margin: "0 0 0.25rem" }}>
          {order.listing_title}
        </p>
      )}
      <p style={{ fontSize: "14px", color: "var(--muted)", margin: "0 0 1.5rem" }}>
        {amountLabel} paid · Order {orderRef}
      </p>

      <div
        style={{
          background: "rgba(79,157,105,0.07)",
          border: "1px solid rgba(79,157,105,0.25)",
          borderRadius: "var(--radius)",
          padding: "1rem 1.25rem",
          marginBottom: "1.5rem",
          textAlign: "left",
        }}
      >
        <p style={{ fontSize: "13px", color: "#3a7d55", margin: 0, lineHeight: 1.6 }}>
          A payment confirmation has been recorded. Our team will contact you within 24 hours to arrange secure delivery.
        </p>
      </div>

      <Link
        to="/dashboard"
        style={{
          display: "block",
          width: "100%",
          padding: "14px 16px",
          background: "var(--gold)",
          color: "#fff",
          borderRadius: "var(--radius)",
          fontWeight: 700,
          fontSize: "15px",
          textAlign: "center",
          textDecoration: "none",
          marginBottom: "1rem",
        }}
      >
        View My Dashboard
      </Link>
      <Link to="/auctions" style={{ fontSize: "13px", color: "var(--gold-dark)" }}>
        Return to Browse Auctions
      </Link>
    </main>
  );
}

export default function Checkout() {
  const { orderId } = useParams();
  const navigate = useNavigate();

  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [deliveryAddress, setDeliveryAddress] = useState("");
  const [starting, setStarting] = useState(false);

  const [stripePromise, setStripePromise] = useState(null);
  const [clientSecret, setClientSecret] = useState(null);
  const [demo, setDemo] = useState(false);
  const [paid, setPaid] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        setLoading(true);
        setError("");
        const data = await getOrderDetail(orderId);
        if (!mounted) return;
        setOrder(data);
        setDeliveryAddress(data.delivery_address_snapshot || "");
        if (data.fulfillment_status !== "pending_payment") {
          navigate(`/orders/${orderId}`, { replace: true });
        }
      } catch (err) {
        if (mounted) setError(err?.response?.data?.detail || "Unable to load this order.");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => { mounted = false; };
  }, [orderId, navigate]);

  const amountLabel = order ? formatMoney(order.amount, order.currency) : "";
  const orderRef = order?.order_ref || `SB-${String(orderId).toUpperCase().slice(0, 8)}`;
  const wonDate = formatDate(order?.won_at);
  const lotRef = String(orderId).toUpperCase().slice(0, 8);

  const handleStartPayment = async () => {
    setStarting(true);
    setError("");
    try {
      const intent = await createPaymentIntent(orderId, deliveryAddress);
      if (intent.demo || !intent.client_secret) {
        setDemo(true);
        return;
      }
      setStripePromise(loadStripe(intent.publishable_key));
      setClientSecret(intent.client_secret);
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not start checkout. Please try again.");
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <main style={{ maxWidth: 1000, margin: "3rem auto", padding: "0 1.5rem" }}>
        <p style={{ color: "var(--muted)" }}>Loading order…</p>
      </main>
    );
  }

  if (error && !order) {
    return (
      <main style={{ maxWidth: 1000, margin: "3rem auto", padding: "0 1.5rem" }}>
        <p className="eyebrow">Secure Checkout</p>
        <h1 style={{ fontFamily: "var(--font-serif)", fontSize: "2rem", marginBottom: "1.5rem" }}>Checkout</h1>
        <p className="form-error">{error}</p>
        <Link to="/dashboard" className="link-gold">← Back to dashboard</Link>
      </main>
    );
  }

  if (paid) {
    return <CheckoutSuccess order={order} amountLabel={amountLabel} orderRef={orderRef} />;
  }

  return (
    <main style={{ maxWidth: 1000, margin: "0 auto", padding: "2.5rem 1.5rem 4rem" }}>
      <p className="eyebrow">Secure Checkout</p>
      <h1 style={{ fontFamily: "var(--font-serif)", fontSize: "2rem", marginBottom: "2rem" }}>
        Complete Your Acquisition
      </h1>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 3fr", gap: "1.5rem", alignItems: "start" }}>

        {/* ── Left: Order Summary ── */}
        <div
          style={{
            background: "var(--panel)",
            border: "1px solid var(--line)",
            borderRadius: "var(--radius)",
            padding: "1.5rem",
          }}
        >
          <p style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--muted)", margin: "0 0 1.25rem" }}>
            Order Summary
          </p>

          <div style={{ display: "flex", gap: "0.875rem", marginBottom: "1.25rem" }}>
            <div
              style={{
                width: 76, height: 76, flexShrink: 0,
                background: "var(--line)", borderRadius: 4,
                overflow: "hidden",
              }}
            >
              {order?.listing_image_url && (
                <img
                  src={order.listing_image_url}
                  alt={order?.listing_title}
                  style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                />
              )}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--gold-dark)", margin: "0 0 3px" }}>
                Lot #{lotRef}
              </p>
              <p style={{ fontSize: "14px", fontWeight: 700, color: "var(--ink)", margin: "0 0 3px", lineHeight: 1.3 }}>
                {order?.listing_title}
              </p>
              {wonDate !== "-" && (
                <p style={{ fontSize: "12px", color: "var(--muted)", margin: 0 }}>Won {wonDate}</p>
              )}
            </div>
          </div>

          <div style={{ borderTop: "1px solid var(--line)", paddingTop: "1rem", marginBottom: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <span style={{ fontSize: "13px", color: "var(--ink-soft)" }}>Hammer Price</span>
              <span style={{ fontSize: "14px", fontWeight: 600, color: "var(--ink)" }}>{amountLabel}</span>
            </div>
          </div>

          <div style={{ borderTop: "1px solid var(--line)", paddingTop: "1rem", marginBottom: "1.25rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <span style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--ink)" }}>
                Total Due
              </span>
              <span style={{ fontFamily: "var(--font-serif)", fontSize: "1.4rem", fontWeight: 700, color: "var(--gold-dark)" }}>
                {amountLabel}
              </span>
            </div>
          </div>

          <div
            style={{
              background: "rgba(79,157,105,0.07)",
              border: "1px solid rgba(79,157,105,0.25)",
              borderRadius: "var(--radius)",
              padding: "0.75rem 1rem",
              marginBottom: "0.875rem",
            }}
          >
            <p style={{ fontSize: "12px", color: "#3a7d55", margin: 0, lineHeight: 1.5 }}>
              Complete payment to confirm your acquisition · 72h window
            </p>
          </div>

          <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0, textAlign: "center", lineHeight: 1.5 }}>
            Payment is a binding contract on the winning bid.
          </p>
        </div>

        {/* ── Right: Payment panel ── */}
        <div
          style={{
            background: "var(--panel)",
            border: "1px solid var(--line)",
            borderRadius: "var(--radius)",
            padding: "1.5rem",
          }}
        >
          <div
            style={{
              display: "flex", alignItems: "center", gap: "0.5rem",
              paddingBottom: "1rem", marginBottom: "1.25rem",
              borderBottom: "1px solid var(--line)",
            }}
          >
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--green)", flexShrink: 0 }} />
            <span style={{ fontSize: "11px", color: "var(--muted)" }}>
              Powered by Stripe Elements · Card data never reaches our servers · 256-bit TLS
            </span>
          </div>

          {!clientSecret && !demo && (
            <>
              <p style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--muted)", margin: "0 0 1rem" }}>
                Delivery Address
              </p>
              <div className="field">
                <textarea
                  rows={3}
                  placeholder="Full delivery address"
                  value={deliveryAddress}
                  onChange={(e) => setDeliveryAddress(e.target.value)}
                  style={{ resize: "vertical" }}
                  required
                />
              </div>
              {error && <p className="form-error">{error}</p>}
              <button
                type="button"
                className="btn-gold"
                disabled={starting || !deliveryAddress.trim()}
                onClick={handleStartPayment}
                style={{ marginTop: "0.5rem" }}
              >
                {starting ? "Preparing…" : "Proceed to Payment"}
              </button>
            </>
          )}

          {demo && (
            <div style={{ padding: "1rem", background: "rgba(180,69,47,0.05)", border: "1px solid rgba(180,69,47,0.2)", borderRadius: "var(--radius)" }}>
              <p style={{ fontSize: "13px", color: "var(--danger)", margin: 0 }}>
                Stripe test keys are not configured on the server. Add{" "}
                <code>STRIPE_SECRET_KEY</code> and <code>STRIPE_PUBLISHABLE_KEY</code> to the backend to enable checkout.
              </p>
            </div>
          )}

          {clientSecret && stripePromise && (
            <>
              <p style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--muted)", margin: "0 0 1rem" }}>
                Payment Details
              </p>
              <Elements stripe={stripePromise} options={{ clientSecret }}>
                <PaymentForm amountLabel={amountLabel} orderId={orderId} onPaid={() => setPaid(true)} />
              </Elements>
              <p style={{ fontSize: "11px", color: "var(--muted)", marginTop: "1rem", textAlign: "center" }}>
                Test mode — card 4242 4242 4242 4242 · any future date · any CVC
              </p>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
