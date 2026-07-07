import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import AuthLayout from "./AuthLayout.jsx";
import { BRAND } from "../../config/brand.js";
import { useAuth } from "../../context/AuthContext.jsx";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleCredentials = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const result = await login(email, password);
      if (result?.mfa_required) {
        navigate("/mfa-verify");
      } else {
        navigate("/auctions");
      }
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          "Invalid credentials or account not found."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout tagline="The auction begins the moment you sign in. Every lot, every bid — yours to discover.">
      <div className="auth-card">
        <p className="eyebrow">Sign In</p>
        <h2 className="card-title">Welcome Back</h2>
        <p className="card-sub">Access your account to bid, track, and win.</p>

        <form onSubmit={handleCredentials} noValidate>
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
              autoComplete="current-password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <Link to="/forgot-password" className="link-gold forgot">
              Forgot password?
            </Link>
          </div>

          {error && <p className="form-error">{error}</p>}

          <button className="btn-gold" type="submit" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign In to Your Account"}
          </button>
        </form>

        <p className="card-switch">
          New to {BRAND.name}?{" "}
          <Link to="/register" className="link-gold">
            Create an account →
          </Link>
        </p>

        <div className="secure-row">
          <span className="dot" />
          256-bit TLS · MFA available · PDPA compliant
        </div>
      </div>
    </AuthLayout>
  );
}
