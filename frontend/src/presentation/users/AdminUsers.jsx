import { useCallback, useEffect, useMemo, useState } from "react";

import AdminLayout from "../admin-layout/AdminLayout.jsx";
import { deleteAdminUser, demoteStaff, getAdminUsers, promoteUser, sendStaffInvite, terminateSessions, toggleUserLock } from "../../api/auth.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { useConfirm, useAlert } from "../../context/ConfirmContext.jsx";

const ITEMS_PER_PAGE = 10;

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
      className={`au-action-btn${danger ? " au-action-btn--danger" : ""}`}
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
  const confirm = useConfirm();
  const alertModal = useAlert();

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
  const [page, setPage]           = useState(1);

  // ── Invite staff (inline) ───────────────────────────────────────────────────
  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviting, setInviting] = useState(false);
  const [inviteMsg, setInviteMsg] = useState(null);

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
      alertModal(err?.response?.data?.detail || "Action failed. Please try again.");
    } finally {
      setRowAction((prev) => { const next = { ...prev }; delete next[userId]; return next; });
    }
  };

  // ── Demote handler ─────────────────────────────────────────────────────────
  const handleDemote = async (userId) => {
    if (!(await confirm(
      "Demote this staff member to a regular user? This removes their admin access and ends their active sessions immediately."
    ))) return;
    setRowAction((prev) => ({ ...prev, [userId]: "demoting" }));
    try {
      await demoteStaff(userId);
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: "Bidder" } : u))
      );
    } catch (err) {
      alertModal(err?.response?.data?.detail || "Demote failed. Please try again.");
    } finally {
      setRowAction((prev) => { const next = { ...prev }; delete next[userId]; return next; });
    }
  };

  // ── Promote handler ────────────────────────────────────────────────────────
  const handlePromote = async (userId) => {
    if (!(await confirm(
      "Promote this user to a staff member? They will gain admin access and be signed out to refresh their session."
    ))) return;
    setRowAction((prev) => ({ ...prev, [userId]: "promoting" }));
    try {
      await promoteUser(userId);
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: "Staff" } : u))
      );
    } catch (err) {
      alertModal(err?.response?.data?.detail || "Promote failed. Please try again.");
    } finally {
      setRowAction((prev) => { const next = { ...prev }; delete next[userId]; return next; });
    }
  };

  // ── Terminate sessions handler ─────────────────────────────────────────────
  const handleTerminate = async (userId) => {
    if (!(await confirm(
      "End all active sessions for this user? They will be signed out immediately and must log in again."
    ))) return;
    setRowAction((prev) => ({ ...prev, [userId]: "terminating" }));
    try {
      await terminateSessions(userId);
    } catch (err) {
      alertModal(err?.response?.data?.detail || "Failed to end sessions. Please try again.");
    } finally {
      setRowAction((prev) => { const next = { ...prev }; delete next[userId]; return next; });
    }
  };

  // ── Delete handler ─────────────────────────────────────────────────────────
  const handleDelete = async (userId) => {
    if (!(await confirm(
      "Delete this user? This permanently removes their account and cannot be undone.",
      { danger: true, confirmLabel: "Delete" }
    ))) return;
    setRowAction((prev) => ({ ...prev, [userId]: "deleting" }));
    try {
      await deleteAdminUser(userId);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch (err) {
      alertModal(err?.response?.data?.detail || "Delete failed. Please try again.");
    } finally {
      setRowAction((prev) => { const next = { ...prev }; delete next[userId]; return next; });
    }
  };

  // ── Invite handler ─────────────────────────────────────────────────────────
  const handleInvite = async (e) => {
    e.preventDefault();
    setInviteMsg(null);
    setInviting(true);
    try {
      const data = await sendStaffInvite(inviteEmail);
      setInviteMsg({ type: "success", text: data.detail });
      setInviteEmail("");
    } catch (err) {
      setInviteMsg({
        type: "error",
        text: err?.response?.data?.detail || "Failed to send invitation. Please try again.",
      });
    } finally {
      setInviting(false);
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

  // Reset to page 1 whenever the filtered set changes
  useEffect(() => { setPage(1); }, [search, roleFilter, statusFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / ITEMS_PER_PAGE));
  const paged = filtered.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <AdminLayout>
      <p className="admin-eyebrow">SecureBid Admin Panel</p>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: ".75rem" }}>
        <h1 className="admin-page-title">Users</h1>
        {isSuperuser && !showInvite && (
          <button
            type="button"
            className="au-invite-toggle"
            onClick={() => setShowInvite(true)}
          >
            + Invite Staff
          </button>
        )}
      </div>

      {isSuperuser && showInvite && (
        <div className="au-invite-panel">
          <button
            type="button"
            className="au-invite-close"
            onClick={() => setShowInvite(false)}
            aria-label="Close invite panel"
          >
            ×
          </button>
          <div className="au-invite-icon">✉</div>
          <div className="au-invite-copy">
            <p className="cf-eyebrow" style={{ margin: "0 0 .2rem" }}>Invite Staff Member</p>
            <p className="au-invite-sub">An email invite will be sent — the invitee sets their own password.</p>
          </div>
          <form onSubmit={handleInvite} className="au-invite-form">
            <input
              type="email"
              placeholder="colleague@example.com"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              required
              className="au-invite-input"
            />
            <button
              type="submit"
              disabled={inviting || !inviteEmail}
              className="au-invite-submit"
            >
              {inviting ? "Sending…" : "Send Invite"}
            </button>
          </form>
          {inviteMsg && (
            <p className={`au-invite-msg${inviteMsg.type === "success" ? " au-invite-msg--ok" : " au-invite-msg--err"}`}>
              {inviteMsg.text}
            </p>
          )}
        </div>
      )}

      {/* Filter bar */}
      <div className="au-filter-bar">
        <div className="au-search-wrap">
          <svg className="au-search-icon" width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="6.5" cy="6.5" r="5" stroke="currentColor" strokeWidth="1.5" />
            <path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <input
            type="text"
            placeholder="Search by name or email…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="au-search-input"
          />
        </div>
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

      {/* User list */}
      <div className="admin-panel">
        {/* Table */}
        {fetchErr ? (
          <p style={{ padding: "1.5rem 1.25rem", color: "var(--danger)", fontSize: ".85rem" }}>{fetchErr}</p>
        ) : loading ? (
          <p style={{ padding: "1.5rem 1.25rem", opacity: .5, fontSize: ".85rem" }}>Loading users…</p>
        ) : filtered.length === 0 ? (
          <p style={{ padding: "1.5rem 1.25rem", opacity: .5, fontSize: ".85rem" }}>No users match the current filters.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: ".82rem", tableLayout: "fixed" }}>
            <colgroup>
              <col style={{ width: "170px" }} />
              <col />
              <col style={{ width: "90px" }} />
              <col style={{ width: "100px" }} />
              <col style={{ width: "100px" }} />
              <col style={{ width: "400px" }} />
            </colgroup>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(27,26,23,.1)" }}>
                {["Name", "Email", "Role", "Status", "Joined", "Actions"].map((h) => (
                  <th key={h} style={{
                    padding: ".6rem 1.25rem", textAlign: "left",
                    fontSize: ".65rem", textTransform: "uppercase",
                    letterSpacing: ".1em", opacity: .45, fontWeight: 600,
                    whiteSpace: "nowrap",
                  }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paged.map((u) => {
                const busy = rowAction[u.id];
                const isLocked = u.status === "Locked";
                const isProtected = u.role === "Superuser";
                const isSelf = u.id === currentUser?.id;

                return (
                  <tr key={u.id} style={{ borderBottom: "1px solid rgba(27,26,23,.06)" }}>
                    <td style={{ padding: ".7rem 1.25rem", fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {u.display_name || <span style={{ opacity: .4 }}>—</span>}
                    </td>
                    <td style={{ padding: ".7rem 1.25rem", opacity: .65, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{u.email}</td>
                    <td style={{ padding: ".7rem 1.25rem" }}><Badge role={u.role} /></td>
                    <td style={{ padding: ".7rem 1.25rem" }}><StatusDot status={u.status} /></td>
                    <td style={{ padding: ".7rem 1.25rem", opacity: .5, whiteSpace: "nowrap" }}>{formatDate(u.created_at)}</td>
                    <td style={{ padding: ".7rem 1.25rem", whiteSpace: "nowrap" }}>
                      {isProtected || isSelf ? (
                        <span style={{ fontSize: ".72rem", opacity: .35 }}>{isSelf ? "You" : "Protected"}</span>
                      ) : (
                        <span className="au-action-group">
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
                            onClick={() => handleDelete(u.id)}
                            disabled={!!busy}
                          >
                            {busy === "deleting" ? "Deleting…" : "Delete"}
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

      {!loading && !fetchErr && filtered.length > 0 && totalPages > 1 && (
        <div className="au-pagination">
          <button
            type="button"
            className="au-page-btn"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            ← Prev
          </button>
          <span className="au-page-info">
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            className="au-page-btn"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            Next →
          </button>
        </div>
      )}
    </AdminLayout>
  );
}
