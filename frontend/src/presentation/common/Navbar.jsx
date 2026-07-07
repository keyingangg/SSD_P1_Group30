import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import Logo from "./Logo.jsx";
import { useAuth } from "../../context/AuthContext.jsx";

const HIDDEN_ON = ["/", "/login", "/register", "/verify-email", "/forgot-password", "/reset-password", "/accept-invite"];

const ADMIN_NAV = [
  { label: "Overview",     to: "/admin/overview" },
  { label: "Listings",     to: "/admin/listings" },
  { label: "Live Monitor", to: "/admin/live-monitor" },
  { label: "Orders",       to: "/admin/orders" },
  { label: "Users",        to: "/admin/users" },
  { label: "Audit Log",    to: "/admin/audit-log" },
];

function initials(user) {
  if (!user) return "";
  const name = user.display_name || user.email || "";
  return name.slice(0, 2).toUpperCase();
}

export default function Navbar() {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen]       = useState(false);
  const [confirmingLogout, setConfirmingLogout] = useState(false);

  if (HIDDEN_ON.includes(pathname)) return null;

  const isAdmin = user?.is_staff === true;

  const handleLogout = async () => {
    setDropdownOpen(false);
    setConfirmingLogout(false);
    await logout();
    navigate("/");
  };

  const closeDropdown = () => { setDropdownOpen(false); setConfirmingLogout(false); };

  return (
    <nav className={`nav-bar${isAdmin ? " nav-bar--admin" : ""}`}>
      <Link to={isAdmin ? "/admin/overview" : "/auctions"}><Logo /></Link>

      <div className="nav-links">
        {isAdmin ? (
          <>
            {ADMIN_NAV.map(({ label, to }) => (
              <Link key={to} to={to} className={`nav-link${pathname === to ? " active" : ""}`}>
                {label}
              </Link>
            ))}
            <Link to="/auctions" className={`nav-link${pathname === "/auctions" ? " active" : ""}`}>
              Auctions
            </Link>
          </>
        ) : (
          <>
            <Link to="/auctions" className={`nav-link${pathname === "/auctions" ? " active" : ""}`}>
              Auctions
            </Link>
            <Link to="/dashboard" className={`nav-link${pathname === "/dashboard" ? " active" : ""}`}>
              Dashboard
            </Link>
          </>
        )}
      </div>

      <div className="nav-right">
        <button
          className="nav-avatar"
          onClick={() => { setDropdownOpen((o) => !o); setConfirmingLogout(false); }}
          aria-label="Account menu"
        >
          {initials(user)}
        </button>

        {dropdownOpen && (
          <>
            <div
              style={{ position: "fixed", inset: 0, zIndex: 199 }}
              onClick={closeDropdown}
            />
            <div className="nav-dropdown">
              {confirmingLogout ? (
                <>
                  <p style={{ padding: ".5rem .9rem .25rem", fontSize: ".78rem", fontWeight: 600, margin: 0 }}>
                    Sign out?
                  </p>
                  <div style={{ display: "flex", gap: ".4rem", padding: ".25rem .9rem .6rem" }}>
                    <button
                      onClick={handleLogout}
                      style={{
                        flex: 1, padding: ".3rem 0", fontSize: ".75rem", fontWeight: 600,
                        background: "var(--ink)", color: "#fff", textAlign: "center",
                        border: "none", borderRadius: 3, cursor: "pointer",
                      }}
                    >
                      Confirm
                    </button>
                    <button
                      onClick={() => setConfirmingLogout(false)}
                      style={{
                        flex: 1, padding: ".3rem 0", fontSize: ".75rem", textAlign: "center",
                        background: "transparent", color: "var(--ink)",
                        border: "1px solid rgba(27,26,23,.2)", borderRadius: 3, cursor: "pointer",
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <>
                  {!user?.is_staff && (
                    <Link to="/dashboard" onClick={closeDropdown}>
                      My Dashboard
                    </Link>
                  )}
                  <Link to="/account-settings" onClick={closeDropdown}>
                    Account Settings
                  </Link>
                  <div className="nav-dropdown-divider" />
                  <button onClick={() => setConfirmingLogout(true)}>Sign Out</button>
                </>
              )}
            </div>
          </>
        )}
      </div>
    </nav>
  );
}
