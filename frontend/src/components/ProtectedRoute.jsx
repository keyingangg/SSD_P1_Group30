import { Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";
import NotFound from "../pages/NotFound.jsx";

// Guards routes that require authentication. Pass `requireAdmin` to restrict
// a route to admin users.
export default function ProtectedRoute({ children, requireAdmin = false }) {
  const { user, loading } = useAuth();

  if (loading) {
    return null;
  }

  if (!user) {
    return <NotFound />;
  }

  if (requireAdmin && !user.is_staff) {
    return <NotFound />;
  }

  return children;
}
