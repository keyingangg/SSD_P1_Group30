import { useCallback, useEffect, useState } from "react";

import AdminLayout from "../../components/admin/AdminLayout.jsx";
import { getAuditLog } from "../../api/auth.js";
import { useWebSocket } from "../../hooks/useWebSocket.js";

function fmtTimestamp(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-SG", {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
    hour12: false,
  });
}

const TABS = [
  { label: "All Events",     key: "all" },
  { label: "Login / Logout", key: "login_logout" },
  { label: "Bids",           key: "bids" },
  { label: "Admin Actions",  key: "admin_actions" },
  { label: "Payments",       key: "payments" },
  { label: "Errors",         key: "errors" },
];

const SEVERITY_COLOR = {
  success: "#3f9c5f",
  admin:   "#6b4fbb",
  warning: "#c2851a",
  error:   "#c0392b",
};

function SeverityDot({ severity }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 7,
        height: 7,
        borderRadius: "50%",
        background: SEVERITY_COLOR[severity] ?? SEVERITY_COLOR.error,
        flexShrink: 0,
        marginTop: 2,
      }}
    />
  );
}

function UserCell({ display, isAdmin }) {
  if (isAdmin) {
    return <span className="sal-admin-badge">Admin</span>;
  }
  if (display === "System" || display === "—") {
    return <span className="sal-user-name">{display}</span>;
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 4 }}>
      <span className="sal-user-name">{display}</span>
      <span className="sal-role-label">USER</span>
    </div>
  );
}

function exportCsv(rows) {
  const cols = ["Timestamp (UTC)", "User", "Role", "Action", "IP Address", "Device", "Ref"];
  const lines = [
    cols.join(","),
    ...rows.map((r) =>
      [
        r.timestamp,
        r.user_display,
        r.is_admin ? "ADMIN" : "USER",
        `"${r.action_label.replace(/"/g, '""')}"`,
        r.ip_address,
        r.device,
        r.ref,
      ].join(",")
    ),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = `securebid-audit-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function AdminAuditLog() {
  const [rows, setRows]       = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [tab, setTab]         = useState("all");

  const load = useCallback(async (category, showSpinner = false) => {
    if (showSpinner) { setLoading(true); setError(null); }
    try {
      setRows(await getAuditLog(category));
    } catch {
      if (showSpinner) setError("Could not load audit log. Please refresh.");
    } finally {
      if (showSpinner) setLoading(false);
    }
  }, []);

  useEffect(() => { load(tab, true); }, [tab, load]);

  // Catalogue WebSocket — re-fetch immediately when any auction event fires
  const { lastMessage, usingPoll } = useWebSocket("/ws/catalogue/");
  useEffect(() => {
    if (lastMessage?.event === "catalogue_changed") load(tab);
  }, [lastMessage, tab, load]);

  // While WebSocket is healthy: 30 s heartbeat.
  // After WebSocket falls back: poll at ≤5 s to satisfy NFR reconnection policy.
  useEffect(() => {
    const id = setInterval(() => load(tab), usingPoll ? 5000 : 30000);
    return () => clearInterval(id);
  }, [tab, load, usingPoll]);

  return (
    <AdminLayout>
      <h1 className="sal-title">Security Audit Log</h1>

      {/* Tab bar */}
      <div className="sal-tabs-row">
        <div className="sal-tabs">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={`sal-tab${tab === t.key ? " active" : ""}`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>
        <button
          className="sal-export-btn"
          onClick={() => exportCsv(rows)}
          disabled={rows.length === 0}
        >
          Export CSV
        </button>
      </div>

      {/* Table */}
      <div className="sal-table-wrap">
        {error && (
          <p style={{ padding: "1.5rem", color: "var(--danger)", fontSize: ".85rem" }}>{error}</p>
        )}
        {!error && (
          <table className="sal-table">
            <thead>
              <tr>
                {["Timestamp (SGT)", "User / Role", "Action", "IP Address", "Device", "Ref"].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={6} className="sal-empty">Loading…</td>
                </tr>
              )}
              {!loading && rows.length === 0 && (
                <tr>
                  <td colSpan={6} className="sal-empty">No events recorded for this category.</td>
                </tr>
              )}
              {!loading && rows.map((r, i) => (
                <tr key={i}>
                  <td className="sal-ts">{fmtTimestamp(r.timestamp)}</td>
                  <td><UserCell display={r.user_display} isAdmin={r.is_admin} /></td>
                  <td>
                    <div className="sal-action-cell">
                      <SeverityDot severity={r.severity} />
                      <span className="sal-action-text">{r.action_label}</span>
                    </div>
                  </td>
                  <td className="sal-ip">{r.ip_address}</td>
                  <td className="sal-device">{r.device}</td>
                  <td className="sal-ref">{r.ref}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </AdminLayout>
  );
}
