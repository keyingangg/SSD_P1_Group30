import { useEffect, useState } from "react";

import { getMFAStatus, startMFAEnrol, confirmMFAEnrol, unenrolMFA } from "../api/auth.js";

export default function AccountSettings() {
  const [enrolled, setEnrolled] = useState(null);
  const [loading, setLoading] = useState(true);

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
    </main>
  );
}
