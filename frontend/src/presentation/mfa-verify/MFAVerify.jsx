import { useState } from "react";
import { useNavigate } from "react-router-dom";

import AuthLayout from "../auth/AuthLayout.jsx";
import { BRAND } from "../../config/brand.js";
import { verifyMFALogin } from "../../api/auth.js";
import { useAuth } from "../../context/AuthContext.jsx";

export default function MFAVerify() {
  const { refreshUser } = useAuth();
  const navigate = useNavigate();

  const [otpCode, setOtpCode] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleOtp = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await verifyMFALogin(otpCode);
      await refreshUser();
      navigate("/auctions");
    } catch (err) {
      setError(
        err?.response?.data?.detail || "Invalid code. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout tagline="The auction begins the moment you sign in. Every lot, every bid — yours to discover.">
      <div className="auth-card">
        <p className="eyebrow">Two-Factor Authentication</p>
        <h2 className="card-title">Enter Your Code</h2>
        <p className="card-sub">
          Open your authenticator app and enter the 6-digit code for{" "}
          <strong>{BRAND.name}</strong>.
        </p>

        <form onSubmit={handleOtp} noValidate>
          <div className="field">
            <label htmlFor="otp">Verification Code</label>
            <input
              id="otp"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="000000"
              maxLength={6}
              value={otpCode}
              onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ""))}
              autoFocus
              required
            />
          </div>

          {error && <p className="form-error">{error}</p>}

          <button className="btn-gold" type="submit" disabled={submitting}>
            {submitting ? "Verifying…" : "Verify Code"}
          </button>
        </form>

        <p className="card-switch">
          <button
            className="link-gold"
            style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
            onClick={() => navigate("/login")}
          >
            ← Back to sign in
          </button>
        </p>
      </div>
    </AuthLayout>
  );
}
