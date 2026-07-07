import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AdminLayout from "../admin-layout/AdminLayout.jsx";
import { getAdminOrders, updateFulfillmentStatus } from "../../api/payments.js";
import { useConfirm, useAlert } from "../../context/ConfirmContext.jsx";

function fmtSGD(cents) {
  const n = Number(cents) / 100;
  if (!n || Number.isNaN(n)) return "—";
  return `S$${n.toLocaleString("en-SG", { minimumFractionDigits: 0 })}`;
}

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-SG", { day: "2-digit", month: "short", year: "numeric" });
}

const FULFILLMENT_TRANSITIONS = {
  paid: "processing",
  processing: "shipped",
  shipped: "delivered",
};

const STATUS_META = {
  pending_payment: { label: "PAY PENDING",  bg: "rgba(180,69,47,0.08)",  color: "#b4452f", border: "rgba(180,69,47,0.3)" },
  paid:            { label: "PAID",          bg: "rgba(79,157,105,0.1)",  color: "#3a7d55", border: "rgba(79,157,105,0.3)" },
  processing:      { label: "PROCESSING",    bg: "rgba(59,130,246,0.08)", color: "#1d4ed8", border: "rgba(59,130,246,0.25)" },
  shipped:         { label: "DISPATCHED",    bg: "rgba(194,161,90,0.1)",  color: "#a6863f", border: "rgba(194,161,90,0.45)" },
  delivered:       { label: "FULFILLED",     bg: "rgba(107,114,128,0.08)",color: "#4b5563", border: "rgba(107,114,128,0.25)" },
};

const NEXT_LABEL = {
  processing: "Processing",
  shipped:    "Dispatched",
  delivered:  "Fulfilled",
};

const TABS = ["All Orders", "Pay Pending", "Paid", "Processing", "Dispatched", "Fulfilled"];
const TAB_STATUS = {
  "Pay Pending": "pending_payment",
  "Paid":        "paid",
  "Processing":  "processing",
  "Dispatched":  "shipped",
  "Fulfilled":   "delivered",
};

function StatusBadge({ status }) {
  const meta = STATUS_META[status] || { label: status.toUpperCase(), bg: "#f5f5f5", color: "#666", border: "#ccc" };
  return (
    <span
      style={{
        display: "inline-block",
        padding: "3px 10px",
        fontSize: "10px",
        fontWeight: 700,
        letterSpacing: "0.08em",
        background: meta.bg,
        color: meta.color,
        border: `1px solid ${meta.border}`,
        borderRadius: 0,
        whiteSpace: "nowrap",
      }}
    >
      {meta.label}
    </span>
  );
}

export default function AdminOrders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("All Orders");
  const [updating, setUpdating] = useState(null);
  const confirm = useConfirm();
  const alertModal = useAlert();

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setOrders(await getAdminOrders());
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not load orders.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleAdvance = async (order) => {
    const next = FULFILLMENT_TRANSITIONS[order.fulfillment_status];
    if (!next) return;
    const nextLabel = NEXT_LABEL[next] || next;
    if (!(await confirm(`Advance order ${order.order_ref} to "${nextLabel}"?\n\nThis action cannot be reversed.`))) return;
    setUpdating(order.id);
    try {
      await updateFulfillmentStatus(order.id, next);
      setOrders((prev) =>
        prev.map((o) => o.id === order.id ? { ...o, fulfillment_status: next } : o)
      );
    } catch (err) {
      alertModal(err?.response?.data?.detail || "Could not update status.");
    } finally {
      setUpdating(null);
    }
  };

  const filtered = orders.filter((o) => {
    if (tab === "All Orders") return true;
    return o.fulfillment_status === TAB_STATUS[tab];
  });

  const counts = Object.fromEntries(
    Object.entries(TAB_STATUS).map(([label, status]) => [
      label,
      orders.filter((o) => o.fulfillment_status === status).length,
    ])
  );

  return (
    <AdminLayout>
      {/* Header */}
      <p className="admin-eyebrow">SecureBid Admin Panel</p>
      <h1 className="admin-page-title">Orders &amp; Fulfilment</h1>

      {/* Summary strip */}
      <div
        style={{
          display: "flex",
          gap: "1px",
          marginBottom: "1.25rem",
          background: "rgba(27,26,23,0.1)",
          border: "1px solid rgba(27,26,23,0.1)",
          overflow: "hidden",
        }}
      >
        {Object.entries(TAB_STATUS).map(([label, status]) => {
          const meta = STATUS_META[status];
          const count = counts[label] || 0;
          return (
            <div
              key={label}
              style={{
                flex: 1,
                padding: "0.875rem 1rem",
                background: "#fff",
                borderRight: "1px solid rgba(27,26,23,0.08)",
                cursor: "pointer",
              }}
              onClick={() => setTab(label)}
            >
              <p style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: meta.color, margin: "0 0 4px" }}>
                {meta.label}
              </p>
              <p style={{ fontFamily: "var(--font-serif)", fontSize: "1.5rem", fontWeight: 700, color: "var(--ink)", margin: 0, lineHeight: 1 }}>
                {count}
              </p>
            </div>
          );
        })}
      </div>

      {/* Tabs */}
      <div className="al-tabs">
        {TABS.map((t) => (
          <button
            key={t}
            className={`al-tab${tab === t ? " active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t}
            {t !== "All Orders" && counts[t] > 0 && (
              <span
                style={{
                  marginLeft: "6px",
                  fontSize: "10px",
                  fontWeight: 700,
                  padding: "1px 6px",
                  borderRadius: 0,
                  background: tab === t ? "rgba(255,255,255,0.25)" : "rgba(27,26,23,0.1)",
                  color: tab === t ? "#fff" : "var(--ink-soft)",
                }}
              >
                {counts[t]}
              </span>
            )}
          </button>
        ))}
      </div>

      {loading && <p style={{ padding: "1.5rem 0", opacity: 0.6 }}>Loading orders…</p>}
      {error && <p style={{ padding: "1.5rem 0", color: "var(--danger)" }}>{error}</p>}

      {!loading && !error && (
        <div className="al-table-wrap">
          <table className="al-table" style={{ minWidth: 960 }}>
            <thead>
              <tr>
                <th>Order #</th>
                <th>Winner</th>
                <th>Item</th>
                <th>Amount Paid</th>
                <th>Method</th>
                <th>Status</th>
                <th style={{ textAlign: "right" }}>Update (Admin Only)</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ padding: "2rem", opacity: 0.5, textAlign: "center" }}>
                    No orders found.
                  </td>
                </tr>
              )}
              {filtered.map((order) => {
                const nextStatus = FULFILLMENT_TRANSITIONS[order.fulfillment_status];
                const canAdvance = !!nextStatus;
                const isUpdating = updating === order.id;

                return (
                  <tr key={order.id}>
                    {/* Order # */}
                    <td>
                      <p style={{ fontFamily: "var(--font-serif)", fontWeight: 700, fontSize: "14px", color: "var(--ink)", margin: "0 0 2px" }}>
                        {order.order_ref}
                      </p>
                      <Link
                        to={`/orders/${order.id}`}
                        style={{ fontSize: "11px", color: "var(--gold-dark)", textDecoration: "none" }}
                      >
                        View details
                      </Link>
                    </td>

                    {/* Winner */}
                    <td>
                      <p style={{ fontWeight: 600, fontSize: "13px", color: "var(--ink)", margin: "0 0 3px" }}>
                        {order.winner_display}
                      </p>
                      <span
                        style={{
                          fontSize: "10px",
                          fontWeight: 600,
                          color: order.winner_is_verified ? "#3a7d55" : "#b4452f",
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                        }}
                      >
                        <span
                          style={{
                            width: 6, height: 6, borderRadius: "50%",
                            background: order.winner_is_verified ? "#4f9d69" : "#b4452f",
                            display: "inline-block",
                          }}
                        />
                        {order.winner_is_verified ? "Verified" : "Unverified"}
                      </span>
                    </td>

                    {/* Item */}
                    <td>
                      <div className="al-item-cell">
                        <div className="al-thumb">
                          {order.listing_image_url && (
                            <img src={order.listing_image_url} alt="" />
                          )}
                        </div>
                        <p style={{ fontSize: "13px", fontWeight: 500, color: "var(--ink)", margin: 0 }}>
                          {order.listing_title}
                        </p>
                      </div>
                    </td>

                    {/* Amount */}
                    <td>
                      <span className="al-bid">{fmtSGD(order.amount)}</span>
                    </td>

                    {/* Method */}
                    <td>
                      <span
                        style={{
                          fontSize: "12px",
                          color: "var(--ink-soft)",
                          padding: "3px 10px",
                          border: "1px solid var(--line)",
                          borderRadius: 0,
                          whiteSpace: "nowrap",
                        }}
                      >
                        {order.has_delivery_address ? "Delivery" : "Collection"}
                      </span>
                    </td>

                    {/* Status */}
                    <td>
                      <StatusBadge status={order.fulfillment_status} />
                    </td>

                    {/* Update */}
                    <td style={{ textAlign: "right" }}>
                      {canAdvance ? (
                        <button
                          className="al-btn"
                          onClick={() => handleAdvance(order)}
                          disabled={isUpdating}
                          style={{ whiteSpace: "nowrap" }}
                        >
                          {isUpdating ? "Updating…" : `${NEXT_LABEL[nextStatus]} ▾`}
                        </button>
                      ) : (
                        <span style={{ fontSize: "12px", color: "var(--muted)" }}>—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Security note */}
      <div
        style={{
          marginTop: "1.25rem",
          padding: "0.75rem 1.25rem",
          background: "#faf9f7",
          border: "1px solid rgba(27,26,23,0.08)",
          fontSize: "12px",
          color: "var(--muted)",
          display: "flex",
          gap: "1.5rem",
          flexWrap: "wrap",
        }}
      >
        <span>
          <strong style={{ color: "var(--ink-soft)" }}>Forward-only progression</strong> — paid → processing → dispatched → fulfilled. No reversals.
        </span>
        <span>
          <strong style={{ color: "var(--ink-soft)" }}>Server-enforced</strong> — all status changes are validated and audit-logged server-side.
        </span>
        <span>
          <strong style={{ color: "var(--ink-soft)" }}>Restricted</strong> — admin/staff role required. Winner names masked for privacy.
        </span>
      </div>
    </AdminLayout>
  );
}
