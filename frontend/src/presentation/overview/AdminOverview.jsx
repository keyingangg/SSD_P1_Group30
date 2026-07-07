import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import AdminLayout from "../admin-layout/AdminLayout.jsx";
import { BRAND } from "../../config/brand.js";
import { getAdminOverview } from "../../api/auctions.js";
import { useWebSocket } from "../../hooks/useWebSocket.js";

const SGD = (n) => `S$${Number(n).toLocaleString()}`;

function timeAgo(isoString) {
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function timeRemaining(isoString) {
  if (!isoString) return "";
  const diff = Math.floor((new Date(isoString).getTime() - Date.now()) / 1000);
  if (diff <= 0) return null;
  const d = Math.floor(diff / 86400);
  const h = Math.floor((diff % 86400) / 3600);
  const m = Math.floor((diff % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export default function AdminOverview() {
  const [overview, setOverview] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(() => {
    getAdminOverview()
      .then(setOverview)
      .catch(() => setError("Failed to load overview data."));
  }, []);

  // Initial load
  useEffect(() => { refresh(); }, [refresh]);

  // Catalogue WebSocket — re-fetch immediately when any auction changes
  const { lastMessage, usingPoll } = useWebSocket("/ws/catalogue/");
  useEffect(() => {
    if (lastMessage?.event === "catalogue_changed") refresh();
  }, [lastMessage, refresh]);

  // While WebSocket is healthy: 30 s heartbeat.
  // After WebSocket falls back: poll at ≤5 s to satisfy NFR reconnection policy.
  useEffect(() => {
    const id = setInterval(refresh, usingPoll ? 5000 : 30000);
    return () => clearInterval(id);
  }, [refresh, usingPoll]);

  const stats = overview
    ? [
        { label: "Active Listings",  value: String(overview.stats.active_listings),                        sub: "Currently live",      color: "green"  },
        { label: "Pending Payments", value: String(overview.stats.pending_payments),                       sub: "Awaiting checkout",   color: "amber"  },
        { label: "Bids Today",       value: String(overview.stats.bids_today),                             sub: "Across all listings", color: ""       },
        { label: "Registered Users", value: Number(overview.stats.registered_users).toLocaleString(),      sub: "Total accounts",      color: "purple" },
      ]
    : [];

  return (
    <AdminLayout>
      <p className="admin-eyebrow">{BRAND.name} Admin Panel</p>
      <h1 className="admin-page-title">Admin Overview</h1>

      {error && <p style={{ color: "var(--color-error, red)", marginBottom: "1rem" }}>{error}</p>}

      {/* Stat cards */}
      <div className="admin-stats">
        {overview
          ? stats.map((s) => (
              <div key={s.label} className={`admin-stat-card${s.color ? ` ${s.color}` : ""}`}>
                <p className="admin-stat-label">{s.label}</p>
                <p className="admin-stat-value">{s.value}</p>
                <p className="admin-stat-sub">{s.sub}</p>
              </div>
            ))
          : [0, 1, 2, 3].map((i) => (
              <div key={i} className="admin-stat-card" style={{ opacity: 0.4 }}>
                <p className="admin-stat-label">—</p>
                <p className="admin-stat-value">…</p>
                <p className="admin-stat-sub">Loading</p>
              </div>
            ))}
      </div>

      {/* Two-column grid */}
      <div className="admin-grid">
        {/* Audit events */}
        <div className="admin-panel">
          <div className="admin-panel-header">
            <span className="admin-panel-title">Recent Audit Events</span>
          </div>
          <div className="audit-list">
            {overview && overview.audit_events.length === 0 && (
              <p style={{ padding: "1rem", opacity: 0.5 }}>No audit events yet.</p>
            )}
            {(overview?.audit_events ?? []).map((e, i) => (
              <div className="audit-row" key={i}>
                <div className="audit-left">
                  <span className={`audit-dot${e.is_admin ? " admin" : ""}`} />
                  <div>
                    <p className={`audit-actor${e.is_admin ? " admin-actor" : ""}`}>{e.actor}</p>
                    <p className="audit-action">{e.action}</p>
                  </div>
                </div>
                <span className="audit-time">{timeAgo(e.timestamp)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Active auctions */}
        <div className="admin-panel">
          <div className="admin-panel-header">
            <span className="admin-panel-title">Active Auctions</span>
          </div>
          <div className="auction-list">
            {overview && overview.active_auctions.length === 0 && (
              <p style={{ padding: "1rem", opacity: 0.5 }}>No active auctions.</p>
            )}
            {(overview?.active_auctions ?? []).map((a) => {
              const remaining = timeRemaining(a.ends_at);
              const ended = remaining === null;
              return (
                <div className="auction-row" key={a.id}>
                  <div>
                    <p className="auction-lot">Lot {a.lot}</p>
                    <p className="auction-name">{a.name}</p>
                    <p className="auction-bid">{SGD(a.bid)}</p>
                  </div>
                  <span className={`auction-time${ended ? " ended" : ""}`}>
                    {ended ? "ENDED" : remaining}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Alert bar — only shown when there are pending payments */}
      {overview && overview.pending_orders_count > 0 && (
        <div className="admin-alert">
          <div className="admin-alert-left">
            <span className="admin-alert-dot" />
            <p className="admin-alert-text">
              {overview.pending_orders_count}{" "}
              {overview.pending_orders_count === 1 ? "order has" : "orders have"} pending
              payments — winners have been notified.
            </p>
          </div>
          <Link to="/admin/orders" className="admin-alert-btn">
            View Orders
          </Link>
        </div>
      )}
    </AdminLayout>
  );
}
