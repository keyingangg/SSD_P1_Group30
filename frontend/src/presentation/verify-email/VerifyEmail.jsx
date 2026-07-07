import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import AuthLayout from "../auth/AuthLayout.jsx";
import { verifyEmail } from "../../api/auth.js";

// Landing page for the verification link emailed at registration.
// Reads ?token= from the URL and confirms it against the backend.
export default function VerifyEmail() {
  const [params] = useSearchParams();
  const token = params.get("token");

  const [status, setStatus] = useState("verifying"); // verifying | success | error
  const [message, setMessage] = useState("");
  // Prevents React 18 StrictMode double-invoke from sending the token twice,
  // which would mark it used on the first call and fail on the second.
  const called = useRef(false);

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("This verification link is missing its token.");
      return;
    }

    if (called.current) return;
    called.current = true;

    (async () => {
      try {
        const data = await verifyEmail(token);
        setStatus("success");
        setMessage(data?.detail || "Your email has been verified.");
      } catch (err) {
        setStatus("error");
        setMessage(
          err?.response?.data?.detail ||
            "This verification link is invalid or has expired."
        );
      }
    })();
  }, [token]);

  return (
    <AuthLayout tagline="One last step — confirm your email to unlock bidding.">
      <div className="auth-card">
        <div className="verify-status">
          {status === "verifying" && (
            <>
              <div className="status-icon">⏳</div>
              <h2 className="card-title">Verifying…</h2>
              <p className="card-sub">Confirming your verification link.</p>
            </>
          )}

          {status === "success" && (
            <>
              <div className="status-icon" style={{ color: "var(--green)" }}>
                ✓
              </div>
              <h2 className="card-title">Email Verified</h2>
              <p className="card-sub">{message}</p>
              <Link to="/login" className="btn-gold" style={{ display: "block", textAlign: "center", color: "#fff" }}>
                Sign In to Your Account
              </Link>
            </>
          )}

          {status === "error" && (
            <>
              <div className="status-icon" style={{ color: "var(--danger)" }}>
                ✕
              </div>
              <h2 className="card-title">Verification Failed</h2>
              <p className="card-sub">{message}</p>
              <p className="card-switch">
                <Link to="/register" className="link-gold">
                  Register again →
                </Link>
              </p>
            </>
          )}
        </div>
      </div>
    </AuthLayout>
  );
}
