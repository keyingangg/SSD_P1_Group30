import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getOrderDetail } from "../../api/payments.js";

function formatMoney(cents, currency) {
  const value = Number(cents) / 100;
  if (Number.isNaN(value)) return "-";
  const code = (currency || "sgd").toUpperCase();
  const prefix = code === "SGD" ? "S$" : `${code} `;
  return `${prefix}${value.toLocaleString("en-SG", { minimumFractionDigits: 0 })}`;
}

function formatDate(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString("en-SG", { day: "numeric", month: "short", year: "numeric" });
}

const STEPS = [
  {
    key: "paid",
    label: "Payment Confirmed",
    desc: "Your payment has been received and verified.",
  },
  {
    key: "processing",
    label: "Order Processing",
    desc: "Your item is being authenticated, packaged, and prepared for dispatch.",
  },
  {
    key: "shipped",
    label: "Dispatched",
    desc: "Your item has been handed to our secure logistics partner for delivery.",
  },
  {
    key: "delivered",
    label: "Delivered",
    desc: "Item successfully delivered and signature obtained.",
  },
];

const STATUS_ORDER = ["pending_payment", "paid", "processing", "shipped", "delivered"];

const STATUS_LABELS = {
  pending_payment: "Pending Payment",
  paid: "Payment Confirmed",
  processing: "Processing",
  shipped: "Dispatched",
  delivered: "Delivered",
};

function stepStatus(stepKey, currentStatus) {
  const ci = STATUS_ORDER.indexOf(currentStatus);
  const si = STATUS_ORDER.indexOf(stepKey);
  if (si < ci) return "done";
  if (si === ci) return "current";
  return "pending";
}

export default function OrderDetail() {
  const { orderId } = useParams();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        setLoading(true);
        const data = await getOrderDetail(orderId);
        if (mounted) setOrder(data);
      } catch (err) {
        if (mounted) setError(err?.response?.data?.detail || "Unable to load this order.");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => { mounted = false; };
  }, [orderId]);

  if (loading) {
    return (
      <main style={{ maxWidth: 1000, margin: "3rem auto", padding: "0 1.5rem" }}>
        <p style={{ color: "var(--muted)" }}>Loading order…</p>
      </main>
    );
  }

  if (error || !order) {
    return (
      <main style={{ maxWidth: 1000, margin: "3rem auto", padding: "0 1.5rem" }}>
        <p className="form-error">{error || "Order not found."}</p>
        <Link to="/dashboard" className="link-gold">← Back to dashboard</Link>
      </main>
    );
  }

  const amountLabel = formatMoney(order.amount, order.currency);
  const orderRef = order.order_ref || `SB-${String(orderId).toUpperCase().slice(0, 8)}`;
  const wonDate = formatDate(order.won_at);
  const lotRef = String(orderId).toUpperCase().slice(0, 8);
  const currentStatusLabel = STATUS_LABELS[order.fulfillment_status] || order.fulfillment_status;

  return (
    <main style={{ maxWidth: 1000, margin: "0 auto", padding: "2rem 1.5rem 4rem" }}>

      {/* Breadcrumb */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "12px", color: "var(--muted)", marginBottom: "1.25rem" }}>
        <Link to="/dashboard" style={{ color: "var(--muted)", textDecoration: "none" }}>Dashboard</Link>
        <span>›</span>
        <Link to="/dashboard" style={{ color: "var(--muted)", textDecoration: "none" }}>Won Auctions</Link>
        <span>›</span>
        <span style={{ color: "var(--ink)" }}>Order {orderRef}</span>
      </div>

      {/* Page header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "2rem" }}>
        <h1 style={{ fontFamily: "var(--font-serif)", fontSize: "2rem", margin: 0 }}>
          Order &amp; Fulfilment Status
        </h1>
        <span
          style={{
            fontSize: "11px", fontWeight: 700, letterSpacing: "0.1em",
            textTransform: "uppercase",
            padding: "5px 12px",
            borderRadius: 999,
            background: order.fulfillment_status === "delivered"
              ? "rgba(79,157,105,0.12)"
              : order.fulfillment_status === "pending_payment"
              ? "rgba(194,161,90,0.12)"
              : "rgba(59,130,246,0.1)",
            color: order.fulfillment_status === "delivered"
              ? "#3a7d55"
              : order.fulfillment_status === "pending_payment"
              ? "var(--gold-dark)"
              : "#1d4ed8",
            border: order.fulfillment_status === "delivered"
              ? "1px solid rgba(79,157,105,0.3)"
              : order.fulfillment_status === "pending_payment"
              ? "1px solid rgba(194,161,90,0.35)"
              : "1px solid rgba(59,130,246,0.25)",
          }}
        >
          {currentStatusLabel}
        </span>
      </div>

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

          {/* Listing */}
          <div style={{ display: "flex", gap: "0.875rem", marginBottom: "1.25rem" }}>
            <div
              style={{
                width: 76, height: 76, flexShrink: 0,
                background: "var(--line)", borderRadius: 4,
                overflow: "hidden",
              }}
            >
              {order.listing_image_url && (
                <img
                  src={order.listing_image_url}
                  alt={order.listing_title}
                  style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                />
              )}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--gold-dark)", margin: "0 0 3px" }}>
                Lot #{lotRef}
              </p>
              <p style={{ fontSize: "14px", fontWeight: 700, color: "var(--ink)", margin: "0 0 3px", lineHeight: 1.3 }}>
                {order.listing_title}
              </p>
              {wonDate && (
                <p style={{ fontSize: "12px", color: "var(--muted)", margin: 0 }}>Won {wonDate}</p>
              )}
            </div>
          </div>

          {/* Amount */}
          <div style={{ borderTop: "1px solid var(--line)", paddingTop: "1rem", marginBottom: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <span style={{ fontSize: "13px", color: "var(--ink-soft)" }}>Hammer Price</span>
              <span style={{ fontSize: "14px", fontWeight: 600, color: "var(--ink)" }}>{amountLabel}</span>
            </div>
          </div>

          <div style={{ borderTop: "1px solid var(--line)", paddingTop: "1rem", marginBottom: "1.25rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <span style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--ink)" }}>
                Total Paid
              </span>
              <span style={{ fontFamily: "var(--font-serif)", fontSize: "1.4rem", fontWeight: 700, color: "var(--gold-dark)" }}>
                {amountLabel}
              </span>
            </div>
          </div>

          {/* Payment confirmed badge */}
          {order.fulfillment_status !== "pending_payment" && (
            <div
              style={{
                display: "flex", alignItems: "center", gap: "0.5rem",
                padding: "0.65rem 0.875rem",
                background: "rgba(79,157,105,0.07)",
                border: "1px solid rgba(79,157,105,0.25)",
                borderRadius: "var(--radius)",
                marginBottom: "1.25rem",
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4f9d69" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span style={{ fontSize: "12px", color: "#3a7d55", fontWeight: 600 }}>Payment confirmed</span>
            </div>
          )}

          {/* Delivery address */}
          {order.delivery_address_snapshot && (
            <>
              <p style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--muted)", margin: "0 0 0.5rem" }}>
                Delivery Address
              </p>
              <p style={{ fontSize: "13px", color: "var(--ink-soft)", margin: "0 0 1rem", lineHeight: 1.6, whiteSpace: "pre-line" }}>
                {order.delivery_address_snapshot}
              </p>
            </>
          )}

          <Link to="/dashboard" style={{ fontSize: "12px", color: "var(--gold-dark)", textDecoration: "none" }}>
            ← Back to dashboard
          </Link>
        </div>

        {/* ── Right: Fulfillment Timeline ── */}
        <div
          style={{
            background: "var(--panel)",
            border: "1px solid var(--line)",
            borderRadius: "var(--radius)",
            padding: "1.5rem",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "1.5rem" }}>
            <p style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--muted)", margin: 0 }}>
              Fulfilment Status
            </p>
            <span style={{ fontSize: "11px", color: "var(--muted)" }}>Updated by SecureBid · Read-only</span>
          </div>

          {STEPS.map((step, i) => {
            const status = stepStatus(step.key, order.fulfillment_status);
            const isDone = status === "done";
            const isCurrent = status === "current";
            const isPending = status === "pending";

            return (
              <div key={step.key} style={{ display: "flex", gap: "1rem" }}>
                {/* Dot + connector */}
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
                  <div
                    style={{
                      width: 22, height: 22, borderRadius: "50%",
                      border: isPending ? "2px solid var(--line)" : "2px solid #4f9d69",
                      background: isDone ? "#4f9d69" : "var(--panel)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    {isDone && (
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                    {isCurrent && (
                      <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#4f9d69" }} />
                    )}
                  </div>
                  {i < STEPS.length - 1 && (
                    <div
                      style={{
                        width: 2,
                        flex: 1,
                        minHeight: 32,
                        background: isDone ? "#4f9d69" : "var(--line)",
                        margin: "3px 0",
                      }}
                    />
                  )}
                </div>

                {/* Content */}
                <div style={{ flex: 1, paddingBottom: i < STEPS.length - 1 ? "1.25rem" : 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", marginBottom: "0.25rem" }}>
                    <p
                      style={{
                        fontSize: "14px",
                        fontWeight: 700,
                        color: isPending ? "var(--muted)" : "var(--ink)",
                        margin: 0,
                      }}
                    >
                      {step.label}
                    </p>
                    {isCurrent && (
                      <span
                        style={{
                          fontSize: "10px", fontWeight: 700, letterSpacing: "0.08em",
                          textTransform: "uppercase",
                          padding: "2px 8px",
                          background: "rgba(79,157,105,0.1)",
                          color: "#3a7d55",
                          border: "1px solid rgba(79,157,105,0.3)",
                          borderRadius: 999,
                        }}
                      >
                        In Progress
                      </span>
                    )}
                  </div>
                  <p
                    style={{
                      fontSize: "12px",
                      color: isPending ? "var(--line)" : "var(--muted)",
                      margin: 0,
                      lineHeight: 1.5,
                    }}
                  >
                    {isPending ? "Pending" : step.desc}
                  </p>
                </div>
              </div>
            );
          })}

          <div
            style={{
              borderTop: "1px solid var(--line)",
              marginTop: "1.5rem",
              paddingTop: "1rem",
            }}
          >
            <p style={{ fontSize: "11px", color: "var(--muted)", margin: "0 0 0.25rem", lineHeight: 1.6 }}>
              Fulfilment status is updated by the SecureBid team. You will be notified at each stage.
            </p>
            <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>
              All deliveries use secure, insured logistics. Signature required upon receipt.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
