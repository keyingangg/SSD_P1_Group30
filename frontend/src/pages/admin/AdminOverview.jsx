import { Link } from "react-router-dom";

import AdminLayout from "../../components/admin/AdminLayout.jsx";
import { BRAND } from "../../config/brand.js";

const SGD = (n) => `S$${Number(n).toLocaleString()}`;

const STATS = [
  { label: "Active Listings",   value: "12",     sub: "Currently live",      color: "green"  },
  { label: "Pending Payments",  value: "3",      sub: "Awaiting checkout",   color: "amber"  },
  { label: "Bids Today",        value: "47",     sub: "Across all listings", color: ""       },
  { label: "Registered Users",  value: "48,503", sub: "Total accounts",      color: "purple" },
];

const AUDIT_EVENTS = [
  { actor: "k***g",  isAdmin: false, action: "Bid placed — LOT 042 — S$19,000",            time: "2m ago"  },
  { actor: "Admin",  isAdmin: true,  action: "Listing updated — LOT 043",                  time: "5m ago"  },
  { actor: "m***r",  isAdmin: false, action: "Login successful",                            time: "8m ago"  },
  { actor: "Admin",  isAdmin: true,  action: "Fulfilment status changed — Order #LXB-0456", time: "12m ago" },
  { actor: "s***k",  isAdmin: false, action: "Failed login (2/5)",                          time: "18m ago" },
  { actor: "Admin",  isAdmin: true,  action: "New listing created — LOT 051",               time: "24m ago" },
  { actor: "p***l",  isAdmin: false, action: "Payment confirmed — S$107,682",               time: "31m ago" },
  { actor: "a***n",  isAdmin: false, action: "Bid placed — LOT 044 — S$148,000",            time: "45m ago" },
];

const ACTIVE_AUCTIONS = [
  { lot: "042", name: "Rolex Submariner",  bid: 18500,  time: "4h 22m", ended: false },
  { lot: "043", name: "Hermès Birkin 30", bid: 34200,  time: "1d 8h",  ended: false },
  { lot: "044", name: "Patek Nautilus",   bid: 148000, time: "",        ended: true  },
  { lot: "046", name: "Bulgari Serpenti", bid: 88000,  time: "3d 12h", ended: false },
  { lot: "051", name: "AP Royal Oak",     bid: 54000,  time: "6h 50m", ended: false },
];

export default function AdminOverview() {
  return (
    <AdminLayout>
      <p className="admin-eyebrow">{BRAND.name} Admin Panel</p>
      <h1 className="admin-page-title">Admin Overview</h1>

      {/* Stat cards */}
      <div className="admin-stats">
        {STATS.map((s) => (
          <div key={s.label} className={`admin-stat-card${s.color ? ` ${s.color}` : ""}`}>
            <p className="admin-stat-label">{s.label}</p>
            <p className="admin-stat-value">{s.value}</p>
            <p className="admin-stat-sub">{s.sub}</p>
          </div>
        ))}
      </div>

      {/* Two-column grid */}
      <div className="admin-grid">
        {/* Audit events */}
        <div className="admin-panel">
          <div className="admin-panel-header">
            <span className="admin-panel-title">Recent Audit Events</span>
            <span className="admin-panel-sub">NFR-06 · Tamper-evident log</span>
          </div>
          <div className="audit-list">
            {AUDIT_EVENTS.map((e, i) => (
              <div className="audit-row" key={i}>
                <div className="audit-left">
                  <span className={`audit-dot${e.isAdmin ? " admin" : ""}`} />
                  <div>
                    <p className={`audit-actor${e.isAdmin ? " admin-actor" : ""}`}>{e.actor}</p>
                    <p className="audit-action">{e.action}</p>
                  </div>
                </div>
                <span className="audit-time">{e.time}</span>
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
            {ACTIVE_AUCTIONS.map((a) => (
              <div className="auction-row" key={a.lot}>
                <div>
                  <p className="auction-lot">Listing {a.lot}</p>
                  <p className="auction-name">{a.name}</p>
                  <p className="auction-bid">{SGD(a.bid)}</p>
                </div>
                <span className={`auction-time${a.ended ? " ended" : ""}`}>
                  {a.ended ? "ENDED" : a.time}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Alert bar */}
      <div className="admin-alert">
        <div className="admin-alert-left">
          <span className="admin-alert-dot" />
          <p className="admin-alert-text">
            3 orders have pending payments — winners have been notified.
            Payment deadline approaching for Order #LXB-2024-0456 (expires in 2h 18m).
          </p>
        </div>
        <Link to="/admin/orders" className="admin-alert-btn">View Orders</Link>
      </div>
    </AdminLayout>
  );
}
