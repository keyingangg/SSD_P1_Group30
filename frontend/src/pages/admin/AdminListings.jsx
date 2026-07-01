import { useCallback, useEffect, useState } from "react";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import AdminLayout from "../../components/admin/AdminLayout.jsx";
import axiosClient from "../../api/axiosClient.js";
import { deleteListing, getListings } from "../../api/auctions.js";
import { useWebSocket } from "../../hooks/useWebSocket.js";
import { useWebSocket } from "../../hooks/useWebSocket.js";

const TABS = ["All Lots", "Live", "Scheduled", "Ended", "Draft", "Cancelled"];

const TAB_STATUS = {
  "Live": "active",
  "Scheduled": "scheduled",
  "Ended": "ended",
  "Draft": "draft",
  "Cancelled": "cancelled",
};

function fmtDate(val) {
  if (!val) return "—";
  const d = new Date(val);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-SG", { day: "2-digit", month: "short", timeZone: "Asia/Singapore" });
}

function fmtSGD(val) {
  const n = Number(val);
  if (!n) return "—";
  return `S$${n.toLocaleString("en-SG")}`;
}

function runtimeStatus(l) {
  const s = String(l.status || "").toLowerCase();
  if (s === "draft" || s === "cancelled") return s;
  const now = Date.now();
  const start = l.starts_at ? new Date(l.starts_at).getTime() : NaN;
  const end = l.ends_at ? new Date(l.ends_at).getTime() : NaN;
  if (!isNaN(end) && now >= end) return "ended";
  if (!isNaN(start) && now >= start) return "active";
  return "scheduled";
}

function StatusBadge({ listing }) {
  const s = runtimeStatus(listing);
  const map = {
    active: ["al-badge al-badge--live", "LIVE"],
    ended: ["al-badge al-badge--ended", "ENDED"],
    cancelled: ["al-badge al-badge--cancelled", "CANCELLED"],
    scheduled: ["al-badge al-badge--scheduled", "SCHEDULED"],
    draft: ["al-badge al-badge--draft", "DRAFT"],
  };
  const [cls, label] = map[s] || ["al-badge al-badge--draft", s.toUpperCase()];
  return <span className={cls}>{label}</span>;
}

export default function AdminListings() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("All Lots");
  const navigate = useNavigate();

  const { lastMessage, usingPoll } = useWebSocket("/ws/catalogue/");

  const load = useCallback(async () => {
    setError(null);
    try { setListings(await getListings()); }
    catch { setError("Could not load listings. Please refresh."); }
  }, []);

  // Initial load
  useEffect(() => {
    setLoading(true);
    load().finally(() => setLoading(false));
  }, [load]);

  // Refresh immediately when catalogue changes via WebSocket
  useEffect(() => {
    if (lastMessage?.event === "catalogue_changed") load();
  }, [lastMessage, load]);

  // REST polling fallback — ≤5 s when WebSocket is unavailable, 30 s otherwise
  useEffect(() => {
    const id = setInterval(load, usingPoll ? 5000 : 30000);
    return () => clearInterval(id);
  }, [usingPoll, load]);

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this listing? This cannot be undone.")) return;
    try {
      await deleteListing(id);
      setListings(prev => prev.filter(l => l.id !== id));
    } catch (err) {
      alert(err?.response?.data?.detail || "Could not delete listing.");
    }
  };

  const handleCancel = async (id) => {
    if (!window.confirm("Cancel this auction? All bidders will be notified by email.")) return;
    try {
      await axiosClient.post(`/auctions/${id}/cancel/`);
      setListings(prev => prev.map(l => l.id === id ? { ...l, status: "cancelled" } : l));
    } catch (err) {
      alert(err?.response?.data?.detail || "Could not cancel auction.");
    }
  };

  const filtered = listings.filter(l => {
    if (tab === "All Lots") return true;
    return runtimeStatus(l) === TAB_STATUS[tab];
  });

  const isLocked = (l) => runtimeStatus(l) === "active";

  return (
    <AdminLayout>
      {/* Page header */}
      <div className="al-header">
        <div className="al-header-accent" />
        <div className="al-header-row">
          <h1 className="al-title">Auction Listings</h1>
          <Link to="/admin/add-item" className="al-new-btn">+ New Listing</Link>
        </div>
      </div>

      <div className="al-divider" />

      {/* Tabs */}
      <div className="al-tabs">
        {TABS.map(t => (
          <button key={t} className={`al-tab${tab === t ? " active" : ""}`} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>

      {loading && <p style={{ padding: "1.5rem 0", opacity: .6 }}>Loading listings…</p>}
      {error   && <p style={{ padding: "1.5rem 0", color: "var(--danger)" }}>{error}</p>}

      {!loading && !error && (
        <>
          <div className="al-table-wrap">
            <table className="al-table">
              <thead>
                <tr>
                  <th>Lot / Item</th>
                  <th>Category</th>
                  <th>Bid</th>
                  <th>Opens</th>
                  <th>Closes</th>
                  <th>Bids</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 && (
                  <tr><td colSpan={8} style={{ padding: "2rem", opacity: .5, textAlign: "center" }}>No listings found.</td></tr>
                )}
                {filtered.map((l, i) => (
                  <tr key={l.id} className={isLocked(l) ? "al-row--locked" : ""}>
                    {/* Lot / Item */}
                    <td>
                      <div className="al-item-cell">
                        <div className="al-thumb">
                          {l.image_url ? <img src={l.image_url} alt="" /> : null}
                        </div>
                        <div>
                          <p className="al-lot-num">LOT {String(i + 1).padStart(3, "0")}</p>
                          <Link to={`/listings/${l.id}`} className="al-item-name al-item-link">{l.title}</Link>
                        </div>
                      </div>
                    </td>
                    {/* Category */}
                    <td className="al-category">{l.category || "—"}</td>
                    {/* Current bid */}
                    <td className="al-bid">{fmtSGD(l.current_highest_bid)}</td>
                    {/* Opens */}
                    <td className="al-date">{fmtDate(l.starts_at)}</td>
                    {/* Closes */}
                    <td className="al-date">{fmtDate(l.ends_at)}</td>
                    {/* Bid count */}
                    <td className="al-bids">{l.bid_count ?? "—"}</td>
                    {/* Status */}
                    <td><StatusBadge listing={l} /></td>
                    {/* Actions */}
                    <td>
                      <div className="al-actions">
                        {(runtimeStatus(l) === "ended" || runtimeStatus(l) === "cancelled") ? null : isLocked(l) ? (
                          <>
                            <p className="al-locked-note">Active bids — core edit locked</p>
                            <div className="al-action-btns">
                              <button className="al-btn al-btn--danger" onClick={() => handleCancel(l.id)}>Cancel</button>
                            </div>
                          </>
                        ) : (
                          <div className="al-action-btns">
                            <button className="al-btn" onClick={() => navigate(`/admin/add-item?edit=${l.id}`)}>Edit</button>
                            <button className="al-btn al-btn--danger" onClick={() => handleDelete(l.id)}>Delete</button>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

        </>
      )}
    </AdminLayout>
  );
}
