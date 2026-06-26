import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";
import NotFound from "../pages/NotFound.jsx";

// Guards routes that require authentication. Pass `requireAdmin` to restrict
// a route to admin users.
export default function ProtectedRoute({ children, requireAdmin = false }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "60vh" }}>
        <div style={{ width: 32, height: 32, border: "3px solid var(--line)", borderTopColor: "var(--gold)", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requireAdmin && !user.is_staff) {
    return <NotFound />;
  }

  return children;
}
