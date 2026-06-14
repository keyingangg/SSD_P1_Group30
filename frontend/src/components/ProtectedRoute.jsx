import { Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";

// Guards routes that require authentication. Pass `requireAdmin` to restrict
// a route to admin users.
export default function ProtectedRoute({ children, requireAdmin = false }) {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // TODO: render a 403/redirect when requireAdmin and the user is not admin.
  if (requireAdmin && !user.is_staff) {
    return <Navigate to="/" replace />;
  }

  return children;
}
