import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import AdminLayout from "../admin-layout/AdminLayout.jsx";
import { deleteAdminUser, demoteStaff, getAdminUsers, promoteUser, terminateSessions, toggleUserLock } from "../../api/auth.js";
import { useAuth } from "../../context/AuthContext.jsx";

const ROLE_OPTIONS   = ["All", "Superuser", "Staff", "Bidder"];
const STATUS_OPTIONS = ["All", "Active", "Pending", "Locked"];

const ROLE_STYLE = {
  Superuser: { background: "rgba(107,79,187,.12)", color: "#6b4fbb" },
  Staff:     { background: "rgba(194,161,90,.15)",  color: "var(--gold-dark)" },
  Bidder:    { background: "rgba(27,26,23,.07)",    color: "var(--ink)" },
};

const STATUS_COLOR = {
  Active:  "var(--green)",
  Pending: "var(--gold-dark)",
  Locked:  "var(--danger)",
};

const inputStyle = {
  padding: ".5rem .8rem",
  border: "1px solid rgba(27,26,23,.2)",
  borderRadius: 0,
  font: "inherit",
  fontSize: ".82rem",
  background: "var(--input-bg)",
  color: "var(--ink)",
  outline: "none",
};

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric", month: "short", year: "numeric",
  });
}

function Badge({ role }) {
  return (
    <span style={{
      display: "inline-block", padding: ".15rem .55rem", borderRadius: 0,
      fontSize: ".68rem", fontWeight: 600, letterSpacing: ".06em",
      ...ROLE_STYLE[role],
    }}>
      {role}
    </span>
  );
}

function StatusDot({ status }) {
  const color = STATUS_COLOR[status] ?? "var(--ink)";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: ".35rem", fontSize: ".75rem", color }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: color, display: "inline-block" }} />
      {status}
    </span>
  );
}

function ActionBtn({ onClick, disabled, children, danger }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: ".25rem .65rem",
        fontSize: ".72rem",
        fontWeight: 600,
        border: `1px solid ${danger ? "var(--danger)" : "rgba(27,26,23,.2)"}`,
        borderRadius: 0,
        background: "transparent",
        color: danger ? "var(--danger)" : "var(--ink)",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? .4 : 1,
        transition: "opacity .15s",
      }}
    >
      {children}
    </button>
  );
}

export default function AdminUsers() {
  const { user: currentUser } = useAuth();
  // Role management (invite / promote / demote) is restricted to superusers,
  // matching the server-side IsSuperUser permission on those endpoints.
  const isSuperuser = currentUser?.is_superuser;

  // ── User list ──────────────────────────────────────────────────────────────
  const [users, setUsers]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [fetchErr, setFetchErr] = useState(null);

  // ── Per-row action state: { [userId]: "locking"|"deleting"|"confirm-delete" } ──
  const [rowAction, setRowAction] = useState({});

  // ── Filters ────────────────────────────────────────────────────────────────
  const [search, setSearch]       = useState("");
  const [roleFilter, setRole]     = useState("All");
  const [statusFilter, setStatus] = useState("All");

  // ── Data fetching ──────────────────────────────────────────────────────────
  const loadUsers = useCallback(async (showSpinner = false) => {
    if (showSpinner) { setLoading(true); setFetchErr(null); }
    try {
      setUsers(await getAdminUsers());
    } catch {
      if (showSpinner) setFetchErr("Could not load users. Please refresh.");
    } finally {
      if (showSpinner) setLoading(false);
    }
  }, []);

  useEffect(() => { loadUsers(true); }, [loadUsers]);

  // No WebSocket exists for user events — poll every 30 s as a background refresh
  useEffect(() => {
    const id = setInterval(() => loadUsers(), 30000);
    return () => clearInterval(id);
  }, [loadUsers]);

  // ── Lock / Unlock handler ──────────────────────────────────────────────────
  const handleToggleLock = async (userId) => {
    setRowAction((prev) => ({ ...prev, [userId]: "locking" }));
    try {
      const data = await toggleUserLock(userId);
      setUsers((prev) =>
        prev.map((u) =>
          u.id === userId
            ? { ...u, status: data.is_active ? "Active" : "Locked" }
            : u
        )
      );
    } catch (err) {
      alert(err?.response?.data?.detail || "Action failed. Please try again.");
    } finally {
      setRowAction((prev) => { const next = { ...prev }; delete next[userId]; return next; });
    }
  };

  // ── Demote handler ─────────────────────────────────────────────────────────
  const handleDemote = async (userId) => {
    if (!window.confirm(
      "Demote this staff member to a regular user? This removes their admin access and ends their active sessions immediately."
    )) return;
    setRowAction((prev) => ({ ...prev, [userId]: "demoting" }));
    try {
      await demoteStaff(userId);
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: "Bidder" } : u))
      );
    } catch (err) {
      alert(err?.response?.data?.detail || "Demote failed. Please try again.");
    } finally {
      setRowAction((prev) => { const next = { ...prev }; delete next[userId]; return next; });
    }
  };

  // ── Promote handler ────────────────────────────────────────────────────────
  const handlePromote = async (userId) => {
    if (!window.confirm(
      "Promote this user to a staff member? They will gain admin access and be signed out to refresh their session."
    )) return;
    setRowAction((prev) => ({ ...prev, [userId]: "promoting" }));
    try {
      await promoteUser(userId);
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: "Staff" } : u))
      );
    } catch (err) {
      alert(err?.response?.data?.detail || "Promote failed. Please try again.");
    } finally {
      setRowAction((prev) => { const next = { ...prev }; delete next[userId]; return next; });
    }
  };

  // ── Terminate sessions handler ─────────────────────────────────────────────
  const handleTerminate = async (userId) => {
    if (!window.confirm(
      "End all active sessions for this user? They will be signed out immediately and must log in again."
    )) return;
    setRowAction((prev) => ({ ...prev, [userId]: "terminating" }));
    try {
      await terminateSessions(userId);
    } catch (err) {
      alert(err?.response?.data?.detail || "Failed to end sessions. Please try again.");
    } finally {
      setRowAction((prev) => { const next = { ...prev }; delete next[userId]; return next; });
    }
  };

  // ── Delete handler ─────────────────────────────────────────────────────────
  const handleDelete = async (userId) => {
    setRowAction((prev) => ({ ...prev, [userId]: "deleting" }));
    try {
      await deleteAdminUser(userId);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch (err) {
      alert(err?.response?.data?.detail || "Delete failed. Please try again.");
    } finally {
      setRowAction((prev) => { const next = { ...prev }; delete next[userId]; return next; });
    }
  };

  // ── Filtered list ──────────────────────────────────────────────────────────
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return users.filter((u) => {
      if (roleFilter   !== "All" && u.role   !== roleFilter)   return false;
      if (statusFilter !== "All" && u.status !== statusFilter) return false;
      if (q && !u.email.toLowerCase().includes(q) && !(u.display_name ?? "").toLowerCase().includes(q)) return false;
      return true;
    });
  }, [users, search, roleFilter, statusFilter]);

  const hasFilters = search || roleFilter !== "All" || statusFilter !== "All";

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <AdminLayout>
      <p className="admin-eyebrow">SecureBid Admin Panel</p>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: ".75rem" }}>
        <h1 className="admin-page-title">Users</h1>
        {isSuperuser && (
          <Link to="/admin/invite-staff" className="admin-alert-btn" style={{ padding: ".57rem 1.25rem", textDecoration: "none" }}>
            Invite Staff
          </Link>
        )}
      </div>

      {/* User list */}
      <div className="admin-panel">
        <div className="admin-panel-header">
          <span className="admin-panel-title">All Accounts</span>
          <span className="admin-panel-sub">
            {loading ? "Loading…" : `${filtered.length} of ${users.length} user${users.length !== 1 ? "s" : ""}`}
          </span>
        </div>

        {/* Filter bar */}
        <div style={{
          padding: ".9rem 1.25rem",
          borderBottom: "1px solid rgba(27,26,23,.08)",
          display: "flex", gap: ".6rem", flexWrap: "wrap", alignItems: "center",
        }}>
          <input
            type="text"
            placeholder="Search by name or email…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ ...inputStyle, minWidth: 220, flex: 1 }}
          />
          <select value={roleFilter} onChange={(e) => setRole(e.target.value)} style={inputStyle}>
            {ROLE_OPTIONS.map((r) => <option key={r}>{r}</option>)}
          </select>
          <select value={statusFilter} onChange={(e) => setStatus(e.target.value)} style={inputStyle}>
            {STATUS_OPTIONS.map((s) => <option key={s}>{s}</option>)}
          </select>
          {hasFilters && (
            <button
              onClick={() => { setSearch(""); setRole("All"); setStatus("All"); }}
              style={{ ...inputStyle, cursor: "pointer", background: "transparent", color: "var(--gold-dark)", borderColor: "var(--gold-dark)", whiteSpace: "nowrap" }}
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Table */}
        {fetchErr ? (
          <p style={{ padding: "1.5rem 1.25rem", color: "var(--danger)", fontSize: ".85rem" }}>{fetchErr}</p>
        ) : loading ? (
          <p style={{ padding: "1.5rem 1.25rem", opacity: .5, fontSize: ".85rem" }}>Loading users…</p>
        ) : filtered.length === 0 ? (
          <p style={{ padding: "1.5rem 1.25rem", opacity: .5, fontSize: ".85rem" }}>No users match the current filters.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: ".82rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(27,26,23,.1)" }}>
                {["Name", "Email", "Role", "Status", "Joined", "Actions"].map((h) => (
                  <th key={h} style={{
                    padding: ".6rem 1.25rem", textAlign: "left",
                    fontSize: ".65rem", textTransform: "uppercase",
                    letterSpacing: ".1em", opacity: .45, fontWeight: 600,
                  }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((u) => {
                const busy = rowAction[u.id];
                const confirmingDelete = busy === "confirm-delete";
                const isLocked = u.status === "Locked";
                const isProtected = u.role === "Superuser";
                const isSelf = u.id === currentUser?.id;

                return (
                  <tr key={u.id} style={{ borderBottom: "1px solid rgba(27,26,23,.06)" }}>
                    <td style={{ padding: ".7rem 1.25rem", fontWeight: 500 }}>
                      {u.display_name || <span style={{ opacity: .4 }}>—</span>}
                    </td>
                    <td style={{ padding: ".7rem 1.25rem", opacity: .65 }}>{u.email}</td>
                    <td style={{ padding: ".7rem 1.25rem" }}><Badge role={u.role} /></td>
                    <td style={{ padding: ".7rem 1.25rem" }}><StatusDot status={u.status} /></td>
                    <td style={{ padding: ".7rem 1.25rem", opacity: .5 }}>{formatDate(u.created_at)}</td>
                    <td style={{ padding: ".7rem 1.25rem" }}>
                      {isProtected || isSelf ? (
                        <span style={{ fontSize: ".72rem", opacity: .35 }}>{isSelf ? "You" : "Protected"}</span>
                      ) : confirmingDelete ? (
                        /* Inline delete confirmation */
                        <span style={{ display: "inline-flex", gap: ".4rem", alignItems: "center" }}>
                          <span style={{ fontSize: ".72rem", color: "var(--danger)", fontWeight: 600 }}>Delete?</span>
                          <ActionBtn
                            danger
                            onClick={() => handleDelete(u.id)}
                            disabled={busy === "deleting"}
                          >
                            {busy === "deleting" ? "Deleting…" : "Confirm"}
                          </ActionBtn>
                          <ActionBtn onClick={() => setRowAction((prev) => { const next = { ...prev }; delete next[u.id]; return next; })}>
                            Cancel
                          </ActionBtn>
                        </span>
                      ) : (
                        <span style={{ display: "inline-flex", gap: ".4rem" }}>
                          <ActionBtn
                            onClick={() => handleToggleLock(u.id)}
                            disabled={!!busy}
                          >
                            {busy === "locking" ? "…" : isLocked ? "Unlock" : "Lock"}
                          </ActionBtn>
                          {isSuperuser && u.role === "Staff" && (
                            <ActionBtn
                              onClick={() => handleDemote(u.id)}
                              disabled={!!busy}
                            >
                              {busy === "demoting" ? "…" : "Demote"}
                            </ActionBtn>
                          )}
                          {isSuperuser && u.role === "Bidder" && (
                            <ActionBtn
                              onClick={() => handlePromote(u.id)}
                              disabled={!!busy}
                            >
                              {busy === "promoting" ? "…" : "Promote"}
                            </ActionBtn>
                          )}
                          <ActionBtn
                            onClick={() => handleTerminate(u.id)}
                            disabled={!!busy}
                          >
                            {busy === "terminating" ? "…" : "End Sessions"}
                          </ActionBtn>
                          <ActionBtn
                            danger
                            onClick={() => setRowAction((prev) => ({ ...prev, [u.id]: "confirm-delete" }))}
                            disabled={!!busy}
                          >
                            Delete
                          </ActionBtn>
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </AdminLayout>
  );
}
