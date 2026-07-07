import { useState } from "react";
import { Link } from "react-router-dom";

import AdminLayout from "../admin-layout/AdminLayout.jsx";
import { sendStaffInvite } from "../../api/auth.js";
import { useAuth } from "../../context/AuthContext.jsx";

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

export default function AdminInviteStaff() {
  const { user: currentUser } = useAuth();
  // Restricted to superusers, matching the server-side IsSuperUser permission
  // on the invite endpoint.
  const isSuperuser = currentUser?.is_superuser;

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviting, setInviting] = useState(false);
  const [inviteMsg, setInviteMsg] = useState(null);

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

  return (
    <AdminLayout>
      <p className="admin-eyebrow">SecureBid Admin Panel</p>
      <h1 className="admin-page-title">Invite Staff</h1>

      {!isSuperuser ? (
        <div className="admin-panel">
          <p style={{ padding: "1.5rem 1.25rem", fontSize: ".85rem", opacity: .65 }}>
            Only superusers can invite staff members.
          </p>
        </div>
      ) : (
        <div className="admin-panel">
          <div className="admin-panel-header">
            <span className="admin-panel-title">Invite Staff Member</span>
            <span className="admin-panel-sub">An email invite will be sent — the invitee sets their own password</span>
          </div>
          <form onSubmit={handleInvite} style={{ padding: "1.25rem", display: "flex", gap: ".75rem", alignItems: "flex-start", flexWrap: "wrap" }}>
            <input
              type="email"
              placeholder="colleague@example.com"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              required
              style={{ ...inputStyle, flex: 1, minWidth: 240 }}
            />
            <button
              type="submit"
              disabled={inviting || !inviteEmail}
              className="admin-alert-btn"
              style={{ padding: ".57rem 1.25rem" }}
            >
              {inviting ? "Sending…" : "Send Invite"}
            </button>
            {inviteMsg && (
              <p style={{
                width: "100%", fontSize: ".82rem", marginTop: ".25rem",
                color: inviteMsg.type === "success" ? "var(--green)" : "var(--danger)",
              }}>
                {inviteMsg.text}
              </p>
            )}
          </form>
        </div>
      )}

      <p style={{ marginTop: "1.25rem" }}>
        <Link to="/admin/users" className="link-gold">
          ← Back to Users
        </Link>
      </p>
    </AdminLayout>
  );
}
