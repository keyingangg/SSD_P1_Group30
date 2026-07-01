import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getMFAStatus, startMFAEnrol, confirmMFAEnrol, unenrolMFA, deleteAccount, changePassword } from "../api/auth.js";
import { useAuth } from "../context/AuthContext.jsx";

export default function AccountSettings() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [enrolled, setEnrolled] = useState(null);
  const [loading, setLoading] = useState(true);

  // Password change state
  const [pwStep, setPwStep]           = useState("idle"); // "idle" | "form"
  const [currentPw, setCurrentPw]     = useState("");
  const [newPw, setNewPw]             = useState("");
  const [confirmPw, setConfirmPw]     = useState("");
  const [pwSubmitting, setPwSubmitting] = useState(false);
  const [pwMessage, setPwMessage]     = useState(null); // { type, text }

  // Delete account state
  const [deleteStep, setDeleteStep]       = useState("idle"); // "idle" | "confirm"
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteOtp, setDeleteOtp]         = useState("");
  const [deleteNeedsMfa, setDeleteNeedsMfa] = useState(false);
  const [deleting, setDeleting]           = useState(false);
  const [deleteError, setDeleteError]     = useState("");

  // Enrolment flow state
  const [enrolStep, setEnrolStep] = useState("idle"); // "idle" | "scan" | "confirm" | "done"
  const [qrCode, setQrCode] = useState(null);
  const [otpCode, setOtpCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState(null); // { type: "success"|"error", text }

  useEffect(() => {
    getMFAStatus()
      .then((d) => setEnrolled(d.enrolled))
      .catch(() => setEnrolled(false))
      .finally(() => setLoading(false));
  }, []);

  const handleStartEnrol = async () => {
    setMessage(null);
    setSubmitting(true);
    try {
      const data = await startMFAEnrol();
      setQrCode(data.qr_code);
      setEnrolStep("scan");
    } catch {
      setMessage({ type: "error", text: "Could not start MFA setup. Please try again." });
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirmEnrol = async (e) => {
    e.preventDefault();
    setMessage(null);
    setSubmitting(true);
    try {
      await confirmMFAEnrol(otpCode);
      setEnrolled(true);
      setEnrolStep("done");
      setMessage({ type: "success", text: "MFA enabled successfully." });
    } catch (err) {
      setMessage({
        type: "error",
        text: err?.response?.data?.detail || "Invalid code. Please try again.",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleUnenrol = async () => {
    if (!window.confirm("Disable MFA? Your account will only be protected by password.")) return;
    setMessage(null);
    setSubmitting(true);
    try {
      await unenrolMFA();
      setEnrolled(false);
      setEnrolStep("idle");
      setQrCode(null);
      setOtpCode("");
      setMessage({ type: "success", text: "MFA disabled." });
    } catch (err) {
      setMessage({
        type: "error",
        text: err?.response?.data?.detail || "Could not disable MFA. Please try again.",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setPwMessage(null);

    if (newPw.length < 12) {
      setPwMessage({ type: "error", text: "New password must be at least 12 characters." });
      return;
    }
    if (newPw !== confirmPw) {
      setPwMessage({ type: "error", text: "Passwords do not match." });
      return;
    }
    if (newPw === currentPw) {
      setPwMessage({ type: "error", text: "New password must differ from your current password." });
      return;
    }

    setPwSubmitting(true);
    try {
      await changePassword({ currentPassword: currentPw, newPassword: newPw });
      // All sessions invalidated server-side — log out and send to login.
      await logout();
      navigate("/login", { replace: true });
    } catch (err) {
      setPwMessage({
        type: "error",
        text: err?.response?.data?.detail || "Could not change password. Please try again.",
      });
    } finally {
      setPwSubmitting(false);
    }
  };

  const handleDeleteSubmit = async (e) => {
    e.preventDefault();
    setDeleteError("");
    setDeleting(true);
    try {
      await deleteAccount({
        currentPassword: deletePassword,
        otpCode: deleteNeedsMfa ? deleteOtp : undefined,
      });
      // Await logout() so user state is cleared before navigating — otherwise
      // Landing.jsx sees the user as still logged in and redirects to /auctions.
      await logout();
      navigate("/", { replace: true });
    } catch (err) {
      const detail = err?.response?.data?.detail || "Could not delete account. Please try again.";
      const needsMfa = err?.response?.data?.mfa_required === true;
      if (needsMfa) {
        setDeleteNeedsMfa(true);
        setDeleteError("Please enter your authenticator code to confirm deletion.");
      } else {
        setDeleteError(detail);
      }
      setDeleting(false);
    }
  };

  return (
    <main style={{ maxWidth: 560, margin: "3rem auto", padding: "0 1.5rem" }}>
      <h1 style={{ marginBottom: "2rem" }}>Account Settings</h1>

      <section
        style={{
          border: "1px solid rgba(27,26,23,.15)",
          borderRadius: 8,
          padding: "1.5rem",
        }}
      >
        <h2 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: ".25rem" }}>
          Two-Factor Authentication
        </h2>
        <p style={{ fontSize: ".85rem", color: "#666", marginBottom: "1.25rem" }}>
          Add an extra layer of security. Once enabled, you'll be asked for a
          6-digit code from your authenticator app each time you sign in.
        </p>

        {loading && <p style={{ fontSize: ".85rem", color: "#888" }}>Loading…</p>}

        {message && (
          <p
            style={{
              fontSize: ".85rem",
              padding: ".6rem .9rem",
              borderRadius: 4,
              marginBottom: "1rem",
              background: message.type === "success" ? "#edfdf1" : "#fdf2f2",
              color: message.type === "success" ? "#1a7f3c" : "#b91c1c",
              border: `1px solid ${message.type === "success" ? "#a7f3c3" : "#fecaca"}`,
            }}
          >
            {message.text}
          </p>
        )}

        {!loading && enrolled && enrolStep !== "idle" && (
          <p style={{ fontSize: ".85rem", color: "#1a7f3c", fontWeight: 600, marginBottom: "1rem" }}>
            ✓ MFA is enabled on your account.
          </p>
        )}

        {!loading && enrolled && (
          <button
            onClick={handleUnenrol}
            disabled={submitting}
            style={{
              padding: ".5rem 1.1rem",
              fontSize: ".85rem",
              fontWeight: 600,
              background: "transparent",
              color: "#b91c1c",
              border: "1px solid #b91c1c",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            {submitting ? "Disabling…" : "Disable MFA"}
          </button>
        )}

        {!loading && !enrolled && enrolStep === "idle" && (
          <button
            onClick={handleStartEnrol}
            disabled={submitting}
            className="btn-gold"
            style={{ fontSize: ".85rem", padding: ".5rem 1.1rem" }}
          >
            {submitting ? "Loading…" : "Enable MFA"}
          </button>
        )}

        {!loading && !enrolled && enrolStep === "scan" && (
          <div>
            <p style={{ fontSize: ".85rem", marginBottom: "1rem" }}>
              Scan this QR code with <strong>Google Authenticator</strong>,{" "}
              <strong>Microsoft Authenticator</strong>, or <strong>Authy</strong>, then
              enter the 6-digit code below to confirm.
            </p>
            {qrCode && (
              <img
                src={`data:image/png;base64,${qrCode}`}
                alt="MFA QR code"
                style={{
                  display: "block",
                  width: 180,
                  height: 180,
                  marginBottom: "1.25rem",
                  border: "1px solid rgba(27,26,23,.1)",
                  borderRadius: 4,
                }}
              />
            )}
            <form onSubmit={handleConfirmEnrol}>
              <div className="field">
                <label htmlFor="otp-confirm" style={{ fontSize: ".85rem" }}>
                  Verification Code
                </label>
                <input
                  id="otp-confirm"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="000000"
                  maxLength={6}
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ""))}
                  required
                  autoFocus
                  style={{ maxWidth: 160 }}
                />
              </div>
              <div style={{ display: "flex", gap: ".75rem", alignItems: "center" }}>
                <button
                  type="submit"
                  disabled={submitting || otpCode.length !== 6}
                  className="btn-gold"
                  style={{ fontSize: ".85rem", padding: ".5rem 1.1rem" }}
                >
                  {submitting ? "Verifying…" : "Confirm & Enable"}
                </button>
                <button
                  type="button"
                  onClick={() => { setEnrolStep("idle"); setQrCode(null); setOtpCode(""); setMessage(null); }}
                  style={{
                    background: "none",
                    border: "none",
                    fontSize: ".82rem",
                    color: "#666",
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}
      </section>

      {/* ── Change Password ───────────────────────────────────────────── */}
      <section style={{ border: "1px solid rgba(27,26,23,.15)", borderRadius: 8, padding: "1.5rem", marginTop: "1.5rem" }}>
        <h2 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: ".25rem" }}>
          Change Password
        </h2>
        <p style={{ fontSize: ".85rem", color: "#666", marginBottom: "1.25rem" }}>
          Update your password. You will be signed out of all devices after changing.
        </p>

        {pwStep === "idle" && (
          <button
            onClick={() => setPwStep("form")}
            className="btn-gold"
            style={{ fontSize: ".85rem", padding: ".5rem 1.1rem" }}
          >
            Change Password
          </button>
        )}

        {pwStep === "form" && (
          <form onSubmit={handlePasswordChange}>
            <div className="field">
              <label htmlFor="current-pw" style={{ fontSize: ".85rem" }}>Current Password</label>
              <input
                id="current-pw"
                type="password"
                autoComplete="current-password"
                placeholder="Enter your current password"
                value={currentPw}
                onChange={(e) => setCurrentPw(e.target.value)}
                required
                autoFocus
              />
            </div>

            <div className="field">
              <label htmlFor="new-pw" style={{ fontSize: ".85rem" }}>New Password</label>
              <input
                id="new-pw"
                type="password"
                autoComplete="new-password"
                placeholder="12+ characters"
                value={newPw}
                onChange={(e) => setNewPw(e.target.value)}
                required
              />
            </div>

            <div className="field">
              <label htmlFor="confirm-pw" style={{ fontSize: ".85rem" }}>Confirm New Password</label>
              <input
                id="confirm-pw"
                type="password"
                autoComplete="new-password"
                placeholder="Repeat new password"
                value={confirmPw}
                onChange={(e) => setConfirmPw(e.target.value)}
                required
              />
            </div>

            {pwMessage && (
              <p style={{
                fontSize: ".85rem", padding: ".6rem .9rem", borderRadius: 4, marginBottom: "1rem",
                background: pwMessage.type === "success" ? "#edfdf1" : "#fdf2f2",
                color: pwMessage.type === "success" ? "#1a7f3c" : "#b91c1c",
                border: `1px solid ${pwMessage.type === "success" ? "#a7f3c3" : "#fecaca"}`,
              }}>
                {pwMessage.text}
              </p>
            )}

            <div style={{ display: "flex", gap: ".75rem", alignItems: "center" }}>
              <button
                type="submit"
                disabled={pwSubmitting || !currentPw || !newPw || !confirmPw}
                className="btn-gold"
                style={{ fontSize: ".85rem", padding: ".5rem 1.1rem" }}
              >
                {pwSubmitting ? "Updating…" : "Update Password"}
              </button>
              <button
                type="button"
                onClick={() => { setPwStep("idle"); setCurrentPw(""); setNewPw(""); setConfirmPw(""); setPwMessage(null); }}
                style={{ background: "none", border: "none", fontSize: ".82rem", color: "#666", cursor: "pointer" }}
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </section>

      {/* ── Delete Account — hidden for admin/staff accounts ─────────── */}
      {!user?.is_staff && <section style={{ border: "1px solid #fecaca", borderRadius: 8, padding: "1.5rem", marginTop: "1.5rem" }}>
        <h2 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: ".25rem", color: "#b91c1c" }}>
          Delete Account
        </h2>
        <p style={{ fontSize: ".85rem", color: "#666", marginBottom: "1.25rem" }}>
          Permanently delete your account and all associated data. This action cannot be undone.
        </p>

        {deleteStep === "idle" && (
          <button
            onClick={() => setDeleteStep("confirm")}
            style={{ padding: ".5rem 1.1rem", fontSize: ".85rem", fontWeight: 600,
              background: "transparent", color: "#b91c1c", border: "1px solid #b91c1c",
              borderRadius: 4, cursor: "pointer" }}
          >
            Delete My Account
          </button>
        )}

        {deleteStep === "confirm" && (
          <form onSubmit={handleDeleteSubmit}>
            <div className="field">
              <label htmlFor="delete-password" style={{ fontSize: ".85rem" }}>
                Current Password
              </label>
              <input
                id="delete-password"
                type="password"
                autoComplete="current-password"
                placeholder="Enter your password to confirm"
                value={deletePassword}
                onChange={(e) => setDeletePassword(e.target.value)}
                required
                autoFocus
              />
            </div>

            {deleteNeedsMfa && (
              <div className="field">
                <label htmlFor="delete-otp" style={{ fontSize: ".85rem" }}>
                  Authenticator Code
                </label>
                <input
                  id="delete-otp"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="000000"
                  maxLength={6}
                  value={deleteOtp}
                  onChange={(e) => setDeleteOtp(e.target.value.replace(/\D/g, ""))}
                  required
                  style={{ maxWidth: 160 }}
                />
              </div>
            )}

            {deleteError && (
              <p style={{ fontSize: ".85rem", color: "#b91c1c", marginBottom: "1rem" }}>
                {deleteError}
              </p>
            )}

            <div style={{ display: "flex", gap: ".75rem", alignItems: "center" }}>
              <button
                type="submit"
                disabled={deleting || !deletePassword || (deleteNeedsMfa && deleteOtp.length !== 6)}
                style={{ padding: ".5rem 1.1rem", fontSize: ".85rem", fontWeight: 600,
                  background: "#b91c1c", color: "#fff", border: "none",
                  borderRadius: 4, cursor: "pointer" }}
              >
                {deleting ? "Deleting…" : "Confirm Delete"}
              </button>
              <button
                type="button"
                onClick={() => { setDeleteStep("idle"); setDeletePassword(""); setDeleteOtp("");
                  setDeleteNeedsMfa(false); setDeleteError(""); }}
                style={{ background: "none", border: "none", fontSize: ".82rem",
                  color: "#666", cursor: "pointer" }}
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </section>}
    </main>
  );
}
