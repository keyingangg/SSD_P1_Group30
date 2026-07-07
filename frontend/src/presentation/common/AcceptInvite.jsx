import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import AuthLayout from "../components/auth/AuthLayout.jsx";
import PasswordStrengthMeter from "../components/auth/PasswordStrengthMeter.jsx";
import { acceptInvite } from "../api/auth.js";
import { BRAND } from "../config/brand.js";

export default function AcceptInvite() {
  const [params] = useSearchParams();
  const token = params.get("token");

  const [displayName, setDisplayName] = useState("");
  const [password, setPassword]       = useState("");
  const [confirm, setConfirm]         = useState("");
  const [status, setStatus]           = useState("idle"); // idle | success | error
  const [error, setError]             = useState("");
  const [submitting, setSubmitting]   = useState(false);

  if (!token) {
    return (
      <AuthLayout tagline="Set up your staff account to access the admin panel.">
        <div className="auth-card">
          <div className="verify-status">
            <div className="status-icon" style={{ color: "var(--danger)" }}>✕</div>
            <h2 className="card-title">Invalid Invitation</h2>
            <p className="card-sub">This invitation link is missing its token. Please use the link from your email.</p>
          </div>
        </div>
      </AuthLayout>
    );
  }

  if (status === "success") {
    return (
      <AuthLayout tagline="Welcome to the team.">
        <div className="auth-card">
          <div className="verify-status">
            <div className="status-icon" style={{ color: "var(--green)" }}>✓</div>
            <h2 className="card-title">Account Ready</h2>
            <p className="card-sub">
              Your {BRAND.name} staff account has been set up. You can now sign in
              to access the admin panel.
            </p>
            <Link
              to="/login"
              className="btn-gold"
              style={{ display: "block", textAlign: "center", marginTop: "1.5rem" }}
            >
              Sign In to Admin Panel
            </Link>
          </div>
        </div>
      </AuthLayout>
    );
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!displayName.trim()) {
      setError("Please enter your display name.");
      return;
    }
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
      await acceptInvite({ token, displayName, password });
      setStatus("success");
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          "This invitation link is invalid or has expired. Please ask an admin to resend it."
      );
      setStatus("error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout tagline="Set up your staff account to access the admin panel.">
      <div className="auth-card">
        <p className="eyebrow">Staff Invitation</p>
        <h2 className="card-title">Set Up Your Account</h2>
        <p className="card-sub">
          You've been invited to join {BRAND.name} as a staff administrator.
          Choose your name and a strong password.
        </p>

        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="displayName">Your Name</label>
            <input
              id="displayName"
              type="text"
              autoComplete="name"
              placeholder="e.g. Jane Smith"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
            />
          </div>

          <div className="field">
            <label htmlFor="password">Password</label>
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

          <button
            className="btn-gold"
            type="submit"
            disabled={submitting || !displayName || !password || !confirm}
          >
            {submitting ? "Setting up…" : "Activate Staff Account"}
          </button>
        </form>
      </div>
    </AuthLayout>
  );
}
