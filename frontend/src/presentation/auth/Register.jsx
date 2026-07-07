import { useState } from "react";
import { Link } from "react-router-dom";

import AuthLayout from "./AuthLayout.jsx";
import PasswordStrengthMeter from "./PasswordStrengthMeter.jsx";
import { BRAND } from "../../config/brand.js";
import { registerUser } from "../../api/auth.js";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    // Client-side checks (server re-validates everything authoritatively).
    if (password.length < 12) {
      setError("Password must be at least 12 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (!agreed) {
      setError("Please accept the Terms of Service and Privacy Policy.");
      return;
    }

    setSubmitting(true);
    try {
      await registerUser({ email, password });
      setSent(true);
    } catch (err) {
      setError(
        err?.response?.data?.password?.[0] ||
          err?.response?.data?.email?.[0] ||
          err?.response?.data?.detail ||
          "Something went wrong. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout tagline="Join 48,500 collectors bidding on authenticated luxury pieces from the world's finest houses.">
      <div className="auth-card">
        {sent ? (
          <div className="auth-sent">
            <div className="sent-icon">✓</div>
            <h2 className="card-title">Check your inbox</h2>
            <p>
              We've sent a verification link to <strong>{email}</strong>. Click
              it to activate your account — the link expires in 24 hours.
            </p>
            <p className="card-switch">
              <Link to="/login" className="link-gold">
                Back to sign in →
              </Link>
            </p>
          </div>
        ) : (
          <>
            <p className="eyebrow">Create Account</p>
            <h2 className="card-title">Join {BRAND.name}</h2>
            <p className="card-sub">
              Register to bid on exclusive authenticated lots.
            </p>

            <form onSubmit={handleSubmit} noValidate>
              <div className="field">
                <label htmlFor="email">Email Address</label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="your@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <div className="field">
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  placeholder="Create a strong password"
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
                  placeholder="Re-enter your password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  required
                />
              </div>

              <label className="check-row">
                <input
                  type="checkbox"
                  checked={agreed}
                  onChange={(e) => setAgreed(e.target.checked)}
                />
                <span>
                  I agree to the{" "}
                  <Link to="/register" className="link-gold">
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link to="/register" className="link-gold">
                    Privacy Policy
                  </Link>
                </span>
              </label>

              {error && <p className="form-error">{error}</p>}

              <button className="btn-gold" type="submit" disabled={submitting}>
                {submitting ? "Creating account…" : "Create My Account"}
              </button>
            </form>

            <p className="card-switch">
              Already have an account?{" "}
              <Link to="/login" className="link-gold">
                Sign in →
              </Link>
            </p>

            <div className="secure-row">
              <span className="dot" />
              Verification email sent after registration. Links expire in 24
              hours.
            </div>
          </>
        )}
      </div>
    </AuthLayout>
  );
}
