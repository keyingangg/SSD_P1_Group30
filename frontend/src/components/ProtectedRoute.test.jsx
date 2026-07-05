import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import ProtectedRoute from "./ProtectedRoute.jsx";
import { useAuth } from "../context/AuthContext.jsx";

vi.mock("../context/AuthContext.jsx", () => ({
  useAuth: vi.fn(),
}));

function renderProtected({ requireAdmin = false } = {}) {
  return render(
    <MemoryRouter initialEntries={["/protected"]}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route
          path="/protected"
          element={
            <ProtectedRoute requireAdmin={requireAdmin}>
              <div>Secret Content</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  it("shows neither the route content nor the login page while auth is pending", () => {
    useAuth.mockReturnValue({ user: null, loading: true });
    renderProtected();
    expect(screen.queryByText("Secret Content")).not.toBeInTheDocument();
    expect(screen.queryByText("Login Page")).not.toBeInTheDocument();
  });

  it("redirects to /login when unauthenticated", () => {
    useAuth.mockReturnValue({ user: null, loading: false });
    renderProtected();
    expect(screen.getByText("Login Page")).toBeInTheDocument();
    expect(screen.queryByText("Secret Content")).not.toBeInTheDocument();
  });

  it("renders the route content when authenticated", () => {
    useAuth.mockReturnValue({ user: { id: "1", is_staff: false }, loading: false });
    renderProtected();
    expect(screen.getByText("Secret Content")).toBeInTheDocument();
  });

  it("blocks a non-staff user from an admin-only route", () => {
    useAuth.mockReturnValue({ user: { id: "1", is_staff: false }, loading: false });
    renderProtected({ requireAdmin: true });
    expect(screen.getByText("404")).toBeInTheDocument();
    expect(screen.getByText("Withdrawn from Catalogue")).toBeInTheDocument();
    expect(screen.queryByText("Secret Content")).not.toBeInTheDocument();
  });

  it("allows a staff user onto an admin-only route", () => {
    useAuth.mockReturnValue({ user: { id: "1", is_staff: true }, loading: false });
    renderProtected({ requireAdmin: true });
    expect(screen.getByText("Secret Content")).toBeInTheDocument();
  });
});
