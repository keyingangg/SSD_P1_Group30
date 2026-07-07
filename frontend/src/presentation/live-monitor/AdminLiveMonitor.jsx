import { useCallback, useEffect, useState } from "react";

import AdminLayout from "../../components/admin/AdminLayout.jsx";
import { getListings } from "../../api/auctions.js";
import { useBidFeed } from "../../hooks/useBidFeed.js";
import { timeAgo } from "../../components/BidFeed.jsx";
import { useWebSocket } from "../../hooks/useWebSocket.js";

const SGD = (n) =>
  `S$${Number(n).toLocaleString("en-SG", { minimumFractionDigits: 0 })}`;

function timeRemaining(isoString) {
  if (!isoString) return null;
  const diff = Math.floor((new Date(isoString).getTime() - Date.now()) / 1000);
  if (diff <= 0) return null;
  const d = Math.floor(diff / 86400);
  const h = Math.floor((diff % 86400) / 3600);
  const m = Math.floor((diff % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function maskBidder(id) {
  if (!id) return "—";
  const code = id.replace(/^Bidder\s*#?/i, "").trim() || id;
  if (code.length <= 1) return code + "***";
  return code[0] + "***" + code[code.length - 1];
}

function shortLot(id) {
  return String(id).replace(/-/g, "").toUpperCase().slice(0, 6);
}

function LiveAuctionCard({ listing }) {
  const { bids } = useBidFeed(listing.id);

  const remaining = timeRemaining(listing.ends_at);
  const topBid = Number(listing.current_highest_bid) || Number(listing.starting_price) || 0;
  const minNext = topBid + Number(listing.minimum_increment || 0);
  const bidCount = bids.length || listing.bid_count || 0;
  const lastThree = bids.slice(0, 3);

  return (
    <div className="lm-card">
      <p className="lm-brand">{listing.category}</p>
      <h2 className="lm-title">{listing.title}</h2>

      <hr className="lm-divider" />

      <div className="lm-stats-row">
        <div className="lm-stat">
          <p className="lm-stat-label">CURRENT BID</p>
          <p className="lm-stat-bid">{SGD(topBid)}</p>
          <p className="lm-stat-next">Min. next: {SGD(minNext)}</p>
        </div>
        <div className="lm-stat">
          <p className="lm-stat-label">BIDS</p>
          <p className="lm-stat-num">{bidCount}</p>
        </div>
        <div className="lm-stat">
          <p className="lm-stat-label">CLOSES</p>
          <p className={`lm-stat-time${remaining === null ? " ended" : ""}`}>
            {remaining ?? "ENDED"}
          </p>
        </div>
      </div>

      <div className="lm-bids">
        <p className="lm-bids-label">LAST 3 BIDS</p>
        {lastThree.length === 0 ? (
          <p className="lm-bids-empty">No bids yet.</p>
        ) : (
          lastThree.map((bid, i) => (
            <div key={bid.id ?? i} className="lm-bid-row">
              <span className="lm-bid-name">{maskBidder(bid.anonymous_identifier)}</span>
              <span className="lm-bid-amount">{SGD(bid.amount)}</span>
              <span className="lm-bid-time">{timeAgo(bid.submitted_at)}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default function AdminLiveMonitor() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(() => {
    getListings()
      .then((data) => {
        setListings(data.filter((l) => l.status === "active"));
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  // Initial load
  useEffect(() => { refresh(); }, [refresh]);

  // Catalogue WebSocket — re-fetch listing list immediately when auctions change
  const { lastMessage, usingPoll } = useWebSocket("/ws/catalogue/");
  useEffect(() => {
    if (lastMessage?.event === "catalogue_changed") refresh();
  }, [lastMessage, refresh]);

  // While WebSocket is healthy: 30 s heartbeat.
  // After WebSocket falls back: poll at ≤5 s to satisfy NFR reconnection policy.
  useEffect(() => {
    const id = setInterval(refresh, usingPoll ? 5000 : 30000);
    return () => clearInterval(id);
  }, [refresh, usingPoll]);

  return (
    <AdminLayout>
      <div className="lm-header">
        <h1 className="lm-page-title">Live Auction Monitor</h1>
        <span className="lm-live-badge">
          <span className="lm-live-badge-dot" />
          LIVE
        </span>
      </div>

      {loading && <p className="lm-empty">Loading active auctions…</p>}
      {!loading && listings.length === 0 && (
        <p className="lm-empty">No live auctions at this time.</p>
      )}

      <div className="lm-grid">
        {listings.map((listing) => (
          <LiveAuctionCard key={listing.id} listing={listing} />
        ))}
      </div>
    </AdminLayout>
  );
}
