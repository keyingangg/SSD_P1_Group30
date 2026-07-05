import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import Dashboard from "./Dashboard.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useWebSocket } from "../hooks/useWebSocket.js";
import { getUserDashboard } from "../api/auctions.js";

vi.mock("../context/AuthContext.jsx", () => ({
  useAuth: vi.fn(),
}));

vi.mock("../hooks/useWebSocket.js", () => ({
  useWebSocket: vi.fn(),
}));

vi.mock("../api/auctions.js", () => ({
  getUserDashboard: vi.fn(),
}));

const DASHBOARD_PAYLOAD = {
  active_bids: [],
  won_auctions: [
    {
      listing_id: "l-pending", order_id: "order-pending", title: "Pending Lot",
      winning_amount: 500, ended_at: "2026-01-01T00:00:00Z", payment_status: "pending",
    },
    {
      listing_id: "l-paid", order_id: "order-paid", title: "Paid Lot",
      winning_amount: 900, ended_at: "2026-01-02T00:00:00Z", payment_status: "paid",
    },
  ],
  payment_status: { total_orders: 2, counts_by_status: {}, pending_payment_auctions: [] },
  auction_history: [],
};

function renderDashboard() {
  useAuth.mockReturnValue({ user: { id: "u1", email: "a@b.com", display_name: "A" } });
  useWebSocket.mockReturnValue({ lastMessage: null, usingPoll: false });
  getUserDashboard.mockResolvedValue(DASHBOARD_PAYLOAD);
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>
  );
}

describe("Dashboard — won-auction order links", () => {
  it("links an unpaid won auction to /checkout/:orderId", async () => {
    renderDashboard();
    const link = await screen.findByRole("link", { name: /Checkout/ });
    expect(link).toHaveAttribute("href", "/checkout/order-pending");
  });

  it("links a paid won auction to /orders/:orderId", async () => {
    renderDashboard();
    const link = await screen.findByRole("link", { name: "View Order" });
    expect(link).toHaveAttribute("href", "/orders/order-paid");
  });
});
