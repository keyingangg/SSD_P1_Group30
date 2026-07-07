import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import AuthLayout from "../components/auth/AuthLayout.jsx";
import PasswordStrengthMeter from "../components/auth/PasswordStrengthMeter.jsx";
import { confirmPasswordReset } from "../api/auth.js";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token");

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [status, setStatus] = useState("idle"); // idle | success | error
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (password.length < 12) {
      setError("Password must be at least 12 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await confirmPasswordReset(token, password);
      setStatus("success");
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          "This reset link is invalid or has expired. Please request a new one."
      );
      setStatus("error");
    } finally {
      setSubmitting(false);
    }
  };

  if (!token) {
    return (
      <AuthLayout tagline="Reset your password to regain access.">
        <div className="auth-card">
          <div className="verify-status">
            <div className="status-icon" style={{ color: "var(--danger)" }}>✕</div>
            <h2 className="card-title">Invalid Link</h2>
            <p className="card-sub">This reset link is missing its token.</p>
            <Link to="/forgot-password" className="link-gold">Request a new link →</Link>
          </div>
        </div>
      </AuthLayout>
    );
  }

  if (status === "success") {
    return (
      <AuthLayout tagline="Your password has been updated.">
        <div className="auth-card">
          <div className="verify-status">
            <div className="status-icon" style={{ color: "var(--green)" }}>✓</div>
            <h2 className="card-title">Password Updated</h2>
            <p className="card-sub">You can now sign in with your new password.</p>
            <Link
              to="/login"
              className="btn-gold"
              style={{ display: "block", textAlign: "center", marginTop: "1.5rem" }}
            >
              Sign In to Your Account
            </Link>
          </div>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout tagline="Choose a new password for your account.">
      <div className="auth-card">
        <p className="eyebrow">Account Recovery</p>
        <h2 className="card-title">Set New Password</h2>
        <p className="card-sub">Must be at least 12 characters and not previously breached.</p>

        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="password">New Password</label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              placeholder="12+ characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <PasswordStrengthMeter password={password} />
          </div>

          <div className="field">
            <label htmlFor="confirm">Confirm Password</label>
            <input
              id="confirm"
              type="password"
              autoComplete="new-password"
              placeholder="Repeat your password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
          </div>

          {error && <p className="form-error">{error}</p>}

          <button className="btn-gold" type="submit" disabled={submitting || !password || !confirm}>
            {submitting ? "Updating…" : "Update Password"}
          </button>
        </form>

        {status === "error" && (
          <p className="card-switch">
            <Link to="/forgot-password" className="link-gold">
              Request a new reset link →
            </Link>
          </p>
        )}
      </div>
    </AuthLayout>
  );
}
