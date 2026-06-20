import { createContext, useContext, useEffect, useState } from "react";

import {
  fetchCsrf,
  getProfile,
  loginUser,
  logoutUser,
} from "../api/auth.js";

const log = (msg, err) => console.error(`[AuthContext] ${msg}`, err);

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On load: prime the CSRF cookie and restore the session if one exists.
  useEffect(() => {
    (async () => {
      try {
        await fetchCsrf();
        const me = await getProfile();
        setUser(me);
      } catch {
        setUser(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const login = async (email, password) => {
    const data = await loginUser({ email, password });
    // If the server requires a TOTP code, don't set user yet — Login.jsx
    // will handle the second step via verifyMFALogin().
    if (data.mfa_required) return data;
    setUser(data);
    return data;
  };

  const logout = async () => {
    try {
      // Refresh CSRF token immediately before the POST — the token may have
      // rotated since the app first loaded (e.g. after login).
      await fetchCsrf();
      await logoutUser();
    } catch (err) {
      log("Logout request failed", err?.response?.status ?? err);
    } finally {
      setUser(null);
    }
  };

  const refreshUser = async () => {
    try {
      const me = await getProfile();
      setUser(me);
      return me;
    } catch {
      setUser(null);
      return null;
    }
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, login, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
