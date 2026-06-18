import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { BRAND } from "../../config/brand.js";
import { useAuth } from "../../context/AuthContext.jsx";

const NAV = [
  { label: "Overview",     to: "/admin/overview" },
  { label: "Listings",     to: "/admin/listings" },
  { label: "Live Monitor", to: "/admin/live-monitor" },
  { label: "Orders",       to: "/admin/orders" },
  { label: "Users",        to: "/admin/users" },
  { label: "Audit Log",    to: "/admin/audit-log" },
  { label: "Settings",     to: "/admin/settings" },
];

function initials(user) {
  const name = user?.display_name || user?.email || "";
  return name.slice(0, 2).toUpperCase();
}

export default function AdminLayout({ children }) {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();
  const navigate = useNavigate();

  const [confirmingLogout, setConfirmingLogout] = useState(false);

  const handleLogout = async () => {
    setConfirmingLogout(false);
    await logout();
    navigate("/");
  };

  return (
    <div className="admin-wrap">
      <aside className="admin-sidebar">
        {/* Compact stacked logo — fits narrow sidebar without overflow */}
        <div className="admin-sidebar-top">
          <Link to="/admin/overview" style={{ textDecoration: "none" }}>
            <div className="admin-sidebar-logo">
              <span className="logo-mark">{BRAND.mark}</span>
              <span className="admin-sidebar-wordmark">{BRAND.name.toUpperCase()}</span>
            </div>
          </Link>
          <div className="admin-brand-badge">ADMIN</div>
        </div>

        <nav className="admin-nav">
          <p className="admin-nav-label">Navigation</p>
          {NAV.map(({ label, to }) => (
            <Link
              key={to}
              to={to}
              className={`admin-nav-link${pathname === to ? " active" : ""}`}
            >
              {label}
            </Link>
          ))}

          <div className="admin-nav-divider" />

          <Link to="/auctions" className="admin-nav-link admin-nav-back">
            ← Back to Auctions
          </Link>
        </nav>

        <div className="admin-sidebar-user">
          {confirmingLogout ? (
            <div style={{ width: "100%" }}>
              <p style={{ fontSize: ".75rem", fontWeight: 600, marginBottom: ".4rem" }}>Sign out?</p>
              <div style={{ display: "flex", gap: ".4rem" }}>
                <button
                  onClick={handleLogout}
                  style={{
                    flex: 1, padding: ".3rem 0", fontSize: ".72rem", fontWeight: 600,
                    background: "var(--ink)", color: "#fff", textAlign: "center",
                    border: "none", borderRadius: 3, cursor: "pointer",
                  }}
                >
                  Confirm
                </button>
                <button
                  onClick={() => setConfirmingLogout(false)}
                  style={{
                    flex: 1, padding: ".3rem 0", fontSize: ".72rem", textAlign: "center",
                    background: "transparent", color: "var(--ink)",
                    border: "1px solid rgba(27,26,23,.2)", borderRadius: 3, cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <>
              <div className="admin-user-avatar">{initials(user)}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p className="admin-user-name">{user?.display_name || "Admin"}</p>
                <p className="admin-user-role">{user?.is_superuser ? "Superuser" : "Staff"}</p>
                <button
                  onClick={() => setConfirmingLogout(true)}
                  style={{
                    background: "none", border: "none", cursor: "pointer",
                    fontSize: ".7rem", fontWeight: 600, color: "var(--ink)",
                    opacity: .45, padding: 0, marginTop: ".25rem",
                    letterSpacing: ".02em", display: "block",
                  }}
                >
                  Sign Out
                </button>
              </div>
            </>
          )}
        </div>
      </aside>

      <main className="admin-main">
        <div className="admin-content">{children}</div>
      </main>
    </div>
  );
}
