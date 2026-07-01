import axios from "axios";

// Django names the CSRF cookie `__Host-csrftoken` when served over HTTPS
// (production, SECURE_SSL=true) and plain `csrftoken` over HTTP (local dev).
// Read whichever is present — preferring the hardened __Host- cookie — so the
// same build works in both environments.
function getCsrfToken() {
  const cookies = document.cookie.split(";").map((c) => c.trim());
  for (const name of ["__Host-csrftoken", "csrftoken"]) {
    const hit = cookies.find((c) => c.startsWith(name + "="));
    if (hit) return decodeURIComponent(hit.slice(name.length + 1));
  }
  return null;
}

// Shared Axios instance. Credentials are included so the Django session cookie
// is sent with every request. The CSRF token is attached manually (below) via a
// request interceptor rather than axios's built-in xsrfCookieName, because that
// only supports a single fixed cookie name and we need to handle both the
// __Host- prefixed (HTTPS) and plain (HTTP) variants.
const axiosClient = axios.create({
  baseURL: "/api",
  withCredentials: true,
  xsrfHeaderName: "X-CSRFToken",
});

// Echo the CSRF cookie back as the X-CSRFToken header on every request. DRF
// SessionAuthentication requires this for unsafe POST/PATCH/DELETE calls.
axiosClient.interceptors.request.use((config) => {
  const token = getCsrfToken();
  if (token) config.headers["X-CSRFToken"] = token;
  return config;
});

export default axiosClient;
