import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import AdminUsers from "./AdminUsers.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import * as authApi from "../../api/auth.js";

vi.mock("../../context/AuthContext.jsx", () => ({
  useAuth: vi.fn(),
}));

vi.mock("../../api/auth.js", () => ({
  getAdminUsers: vi.fn(),
  sendStaffInvite: vi.fn(),
  toggleUserLock: vi.fn(),
  deleteAdminUser: vi.fn(),
  demoteStaff: vi.fn(),
  promoteUser: vi.fn(),
  terminateSessions: vi.fn(),
}));

const SUPERUSER = { id: "viewer-super", is_staff: true, is_superuser: true };
const PLAIN_STAFF = { id: "viewer-staff", is_staff: true, is_superuser: false };

const SAMPLE_USERS = [
  {
    id: "u-bidder", email: "bidder@example.com", display_name: "Bea Bidder",
    role: "Bidder", status: "Active", created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "u-staff", email: "staff@example.com", display_name: "Sam Staff",
    role: "Staff", status: "Active", created_at: "2026-01-02T00:00:00Z",
  },
  {
    id: "u-superuser-other", email: "othersuper@example.com", display_name: "Other Root",
    role: "Superuser", status: "Active", created_at: "2026-01-01T00:00:00Z",
  },
];

function setup(currentUser, users = SAMPLE_USERS) {
  useAuth.mockReturnValue({ user: currentUser });
  authApi.getAdminUsers.mockResolvedValue(users);
  return render(<AdminUsers />);
}

describe("AdminUsers — role management UI gating", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(window, "alert").mockImplementation(() => {});
  });

  it("shows the Invite Staff panel for a superuser", async () => {
    setup(SUPERUSER);
    expect(await screen.findByText("Invite Staff Member")).toBeInTheDocument();
  });

  it("hides the Invite Staff panel for a plain staff account", async () => {
    setup(PLAIN_STAFF);
    await screen.findByText("bidder@example.com");
    expect(screen.queryByText("Invite Staff Member")).not.toBeInTheDocument();
  });

  it("shows Promote only on Bidder rows, for a superuser viewer", async () => {
    setup(SUPERUSER);
    await screen.findByText("bidder@example.com");
    const bidderRow = screen.getByText("bidder@example.com").closest("tr");
    const staffRow = screen.getByText("staff@example.com").closest("tr");
    expect(within(bidderRow).getByText("Promote")).toBeInTheDocument();
    expect(within(staffRow).queryByText("Promote")).not.toBeInTheDocument();
  });

  it("shows Demote only on Staff rows, for a superuser viewer", async () => {
    setup(SUPERUSER);
    await screen.findByText("staff@example.com");
    const staffRow = screen.getByText("staff@example.com").closest("tr");
    const bidderRow = screen.getByText("bidder@example.com").closest("tr");
    expect(within(staffRow).getByText("Demote")).toBeInTheDocument();
    expect(within(bidderRow).queryByText("Demote")).not.toBeInTheDocument();
  });

  it("hides Promote and Demote entirely for a plain-staff viewer", async () => {
    setup(PLAIN_STAFF);
    await screen.findByText("staff@example.com");
    expect(screen.queryByText("Promote")).not.toBeInTheDocument();
    expect(screen.queryByText("Demote")).not.toBeInTheDocument();
  });

  it("shows 'Protected' with no action buttons on another superuser's row", async () => {
    setup(SUPERUSER);
    await screen.findByText("othersuper@example.com");
    const superRow = screen.getByText("othersuper@example.com").closest("tr");
    expect(within(superRow).getByText("Protected")).toBeInTheDocument();
    expect(within(superRow).queryByText("Demote")).not.toBeInTheDocument();
    expect(within(superRow).queryByText("Delete")).not.toBeInTheDocument();
  });

  it("shows 'You' with no action buttons on the viewer's own row", async () => {
    const selfRow = {
      id: SUPERUSER.id, email: "self@example.com", display_name: "Self",
      role: "Superuser", status: "Active", created_at: "2026-01-01T00:00:00Z",
    };
    setup(SUPERUSER, [...SAMPLE_USERS, selfRow]);
    await screen.findByText("self@example.com");
    const ownRow = screen.getByText("self@example.com").closest("tr");
    expect(within(ownRow).getByText("You")).toBeInTheDocument();
    expect(within(ownRow).queryByText("Delete")).not.toBeInTheDocument();
  });

  it("shows 'End Sessions' for a plain-staff viewer even though Promote/Demote are hidden", async () => {
    setup(PLAIN_STAFF);
    await screen.findByText("staff@example.com");
    const staffRow = screen.getByText("staff@example.com").closest("tr");
    expect(within(staffRow).getByText("End Sessions")).toBeInTheDocument();
  });
});

describe("AdminUsers — Lock/Unlock interaction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "alert").mockImplementation(() => {});
  });

  it("locks an active user and flips the button to Unlock", async () => {
    const user = userEvent.setup();
    authApi.toggleUserLock.mockResolvedValue({ detail: "Account locked.", is_active: false });
    setup(SUPERUSER);

    await screen.findByText("bidder@example.com");
    const bidderRow = screen.getByText("bidder@example.com").closest("tr");
    await user.click(within(bidderRow).getByText("Lock"));

    expect(authApi.toggleUserLock).toHaveBeenCalledWith("u-bidder");
    expect(await within(bidderRow).findByText("Unlock")).toBeInTheDocument();
  });
});

describe("AdminUsers — Delete two-step confirmation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "alert").mockImplementation(() => {});
  });

  it("requires a Confirm click before deleting, and Cancel aborts it", async () => {
    const user = userEvent.setup();
    setup(SUPERUSER);

    await screen.findByText("bidder@example.com");
    const bidderRow = screen.getByText("bidder@example.com").closest("tr");
    await user.click(within(bidderRow).getByText("Delete"));

    expect(within(bidderRow).getByText("Delete?")).toBeInTheDocument();
    await user.click(within(bidderRow).getByText("Cancel"));

    expect(authApi.deleteAdminUser).not.toHaveBeenCalled();
    expect(within(bidderRow).getByText("Delete")).toBeInTheDocument();
  });

  it("deletes the user and removes their row once Confirm is clicked", async () => {
    const user = userEvent.setup();
    authApi.deleteAdminUser.mockResolvedValue({ detail: "Account deleted." });
    setup(SUPERUSER);

    await screen.findByText("bidder@example.com");
    const bidderRow = screen.getByText("bidder@example.com").closest("tr");
    await user.click(within(bidderRow).getByText("Delete"));
    await user.click(within(bidderRow).getByText("Confirm"));

    expect(authApi.deleteAdminUser).toHaveBeenCalledWith("u-bidder");
    expect(screen.queryByText("bidder@example.com")).not.toBeInTheDocument();
  });
});
