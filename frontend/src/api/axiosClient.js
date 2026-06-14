import axios from "axios";

// Shared Axios instance. Credentials are included so the Django session cookie
// is sent with every request. Axios automatically reads the CSRF token from the
// `csrftoken` cookie and sends it back as the `X-CSRFToken` header on unsafe
// requests (required by DRF SessionAuthentication for authenticated POST/PATCH/
// DELETE calls).
const axiosClient = axios.create({
  baseURL: "/api",
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  headers: {
    "Content-Type": "application/json",
  },
});

export default axiosClient;
