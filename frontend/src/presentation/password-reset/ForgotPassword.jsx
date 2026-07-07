import { useState } from "react";
import { Link } from "react-router-dom";

import AuthLayout from "../components/auth/AuthLayout.jsx";
import { BRAND } from "../config/brand.js";
import { requestPasswordReset } from "../api/auth.js";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await requestPasswordReset(email);
      setSubmitted(true);
    } catch {
      // Show the sent state even on network error — don't reveal if email exists.
      setSubmitted(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout tagline="Enter your email and we'll send you a link to reset your password.">
      <div className="auth-card">
        {submitted ? (
          <div className="auth-sent">
            <div className="sent-icon">✉</div>
            <h2 className="card-title">Check Your Inbox</h2>
            <p className="card-sub">
              If an account exists for <strong>{email}</strong>, a reset link
              has been sent. It expires in 10 minutes.
            </p>
            <p className="card-sub" style={{ marginTop: ".75rem", opacity: .6, fontSize: ".82rem" }}>
              Didn't receive it? Check your spam folder or{" "}
              <button
                className="link-gold"
                style={{ background: "none", border: "none", cursor: "pointer", font: "inherit", fontSize: "inherit" }}
                onClick={() => { setSubmitted(false); setEmail(""); }}
              >
                try again
              </button>.
            </p>
            <Link to="/login" className="btn-gold" style={{ display: "block", textAlign: "center", marginTop: "1.5rem" }}>
              Back to Sign In
            </Link>
          </div>
        ) : (
          <>
            <p className="eyebrow">Account Recovery</p>
            <h2 className="card-title">Reset Your Password</h2>
            <p className="card-sub">
              Enter the email address on your {BRAND.name} account.
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

              {error && <p className="form-error">{error}</p>}

              <button className="btn-gold" type="submit" disabled={submitting || !email}>
                {submitting ? "Sending…" : "Send Reset Link"}
              </button>
            </form>

            <p className="card-switch">
              Remember it?{" "}
              <Link to="/login" className="link-gold">Back to Sign In →</Link>
            </p>
          </>
        )}
      </div>
    </AuthLayout>
  );
}
