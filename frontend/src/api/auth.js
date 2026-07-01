import axiosClient from "./axiosClient.js";

// Prime the CSRF cookie so authenticated unsafe requests (e.g. logout) succeed.
export async function fetchCsrf() {
  await axiosClient.get("/accounts/csrf/");
}

// Register a new (inactive) account. Triggers a verification email.
export async function registerUser({ email, password }) {
  const { data } = await axiosClient.post("/accounts/register/", {
    email,
    password,
  });
  return data;
}

// Authenticate and start a session. Returns the user profile.
export async function loginUser({ email, password }) {
  const { data } = await axiosClient.post("/accounts/login/", {
    email,
    password,
  });
  return data;
}

// End the current session.
export async function logoutUser() {
  const { data } = await axiosClient.post("/accounts/logout/");
  return data;
}

// Confirm an email verification token from the emailed link.
export async function verifyEmail(token) {
  const { data } = await axiosClient.post("/accounts/verify-email/", { token });
  return data;
}

// Fetch the currently authenticated user's profile (used to restore session).
export async function getProfile() {
  const { data } = await axiosClient.get("/accounts/profile/");
  return data;
}

export async function requestPasswordReset(email) {
  const { data } = await axiosClient.post("/accounts/password-reset/", { email });
  return data;
}

export async function confirmPasswordReset(token, password) {
  const { data } = await axiosClient.post("/accounts/password-reset/confirm/", {
    token,
    password,
  });
  return data;
}

export async function sendStaffInvite(email) {
  const { data } = await axiosClient.post("/accounts/staff/invite/", { email });
  return data;
}

export async function acceptInvite({ token, displayName, password }) {
  const { data } = await axiosClient.post("/accounts/staff/accept-invite/", {
    token,
    display_name: displayName,
    password,
  });
  return data;
}

export async function getAdminUsers() {
  const { data } = await axiosClient.get("/accounts/admin/users/");
  return data;
}

export async function toggleUserLock(userId) {
  const { data } = await axiosClient.patch(`/accounts/admin/users/${userId}/`);
  return data;
}

export async function deleteAdminUser(userId) {
  const { data } = await axiosClient.delete(`/accounts/admin/users/${userId}/`);
  return data;
}

export async function getMFAStatus() {
  const { data } = await axiosClient.get("/accounts/mfa/status/");
  return data;
}

export async function startMFAEnrol() {
  const { data } = await axiosClient.get("/accounts/mfa/enrol/");
  return data;
}

export async function confirmMFAEnrol(otpCode) {
  const { data } = await axiosClient.post("/accounts/mfa/enrol/confirm/", { otp_code: otpCode });
  return data;
}

export async function unenrolMFA() {
  const { data } = await axiosClient.post("/accounts/mfa/unenrol/");
  return data;
}

export async function verifyMFALogin(otpCode) {
  const { data } = await axiosClient.post("/accounts/mfa/verify-login/", { otp_code: otpCode });
  return data;
}

export async function changePassword({ currentPassword, newPassword }) {
  const { data } = await axiosClient.post("/accounts/password-change/", {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return data;
}

export async function deleteAccount({ currentPassword, otpCode }) {
  const payload = { current_password: currentPassword };
  if (otpCode) payload.otp_code = otpCode;
  const { data } = await axiosClient.post("/accounts/delete/", payload);
  return data;
}

export async function getAuditLog(category = "all") {
  const params = category !== "all" ? `?category=${category}` : "";
  const { data } = await axiosClient.get(`/accounts/admin/audit-log/${params}`);
  return data;
}
