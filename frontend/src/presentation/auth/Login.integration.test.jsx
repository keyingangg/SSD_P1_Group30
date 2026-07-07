// Integration tests: real Login + real ProtectedRoute + the real AuthProvider,
// wired together through a real react-router. Only the network boundary
// (api/auth.js) is mocked — this proves the components actually work together,
// unlike the isolated unit tests in ProtectedRoute.test.jsx which mock useAuth.
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import Login from "./Login.jsx";
import MFAVerify from "../mfa-verify/MFAVerify.jsx";
import ProtectedRoute from "../common/ProtectedRoute.jsx";
import { AuthProvider } from "../../context/AuthContext.jsx";
import * as authApi from "../../api/auth.js";

vi.mock("../../api/auth.js", () => ({
  fetchCsrf: vi.fn(),
  getProfile: vi.fn(),
  loginUser: vi.fn(),
  logoutUser: vi.fn(),
  verifyMFALogin: vi.fn(),
}));

function renderApp(initialPath) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/mfa-verify" element={<MFAVerify />} />
          <Route path="/auctions" element={<div>Auctions Page</div>} />
          <Route
            path="/protected"
            element={
              <ProtectedRoute>
                <div>Protected Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("Login — integration with AuthContext and routing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authApi.fetchCsrf.mockResolvedValue();
  });

  it("navigates to /auctions after a successful login", async () => {
    const user = userEvent.setup();
    authApi.getProfile.mockRejectedValue(new Error("no session"));
    authApi.loginUser.mockResolvedValue({ id: "1", email: "a@b.com", is_staff: false });

    renderApp("/login");
    await screen.findByText("Welcome Back");

    await user.type(screen.getByLabelText("Email Address"), "a@b.com");
    await user.type(screen.getByLabelText("Password"), "Password123!");
    await user.click(screen.getByRole("button", { name: "Sign In to Your Account" }));

    expect(await screen.findByText("Auctions Page")).toBeInTheDocument();
  });

  it("shows the server error and stays on the login page on failure", async () => {
    const user = userEvent.setup();
    authApi.getProfile.mockRejectedValue(new Error("no session"));
    authApi.loginUser.mockRejectedValue({
      response: { data: { detail: "Invalid credentials or account not found." } },
    });

    renderApp("/login");
    await screen.findByText("Welcome Back");

    await user.type(screen.getByLabelText("Email Address"), "a@b.com");
    await user.type(screen.getByLabelText("Password"), "WrongPass!");
    await user.click(screen.getByRole("button", { name: "Sign In to Your Account" }));

    expect(
      await screen.findByText("Invalid credentials or account not found.")
    ).toBeInTheDocument();
    expect(screen.getByText("Welcome Back")).toBeInTheDocument();
  });

  it("walks through the MFA step and navigates to /auctions on success", async () => {
    const user = userEvent.setup();
    authApi.getProfile.mockRejectedValue(new Error("no session"));
    authApi.loginUser.mockResolvedValue({ mfa_required: true });
    authApi.verifyMFALogin.mockResolvedValue({ detail: "ok" });

    renderApp("/login");
    await screen.findByText("Welcome Back");

    await user.type(screen.getByLabelText("Email Address"), "a@b.com");
    await user.type(screen.getByLabelText("Password"), "Password123!");
    await user.click(screen.getByRole("button", { name: "Sign In to Your Account" }));

    expect(await screen.findByText("Two-Factor Authentication")).toBeInTheDocument();

    // refreshUser() reads the profile again once MFA succeeds.
    authApi.getProfile.mockResolvedValue({ id: "1", email: "a@b.com", is_staff: false });
    await user.type(screen.getByLabelText("Verification Code"), "123456");
    await user.click(screen.getByRole("button", { name: "Verify Code" }));

    expect(await screen.findByText("Auctions Page")).toBeInTheDocument();
  });

  it("redirects an unauthenticated visitor from a protected route to /login", async () => {
    authApi.getProfile.mockRejectedValue(new Error("no session"));

    renderApp("/protected");

    expect(await screen.findByText("Welcome Back")).toBeInTheDocument();
  });

  it("completes the full loop: blocked, redirected to login, then signs in", async () => {
    const user = userEvent.setup();
    authApi.getProfile.mockRejectedValue(new Error("no session"));
    authApi.loginUser.mockResolvedValue({ id: "1", email: "a@b.com", is_staff: false });

    renderApp("/protected");
    await screen.findByText("Welcome Back");

    await user.type(screen.getByLabelText("Email Address"), "a@b.com");
    await user.type(screen.getByLabelText("Password"), "Password123!");
    await user.click(screen.getByRole("button", { name: "Sign In to Your Account" }));

    // Login always lands on /auctions — it doesn't currently redirect back to
    // the originally requested protected route (ProtectedRoute's `state`
    // param is set but not consumed by Login.jsx).
    expect(await screen.findByText("Auctions Page")).toBeInTheDocument();
  });
});
